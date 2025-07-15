from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from django.db.models import Max
from progress.models import CustomUser, DailyProgress, UserStats, Alert


class Command(BaseCommand):
    help = 'アラートをチェックして生成します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際の処理は行わず、検出内容のみを表示します',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(f'アラートチェック開始: {timezone.now()}')
        )
        
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN モード - 実際の処理は行いません')
            )
        
        # 研修生のみを対象
        students = CustomUser.objects.filter(user_type='student').select_related('stats')
        
        grade_risk_count = 0
        no_report_count = 0
        
        for student in students:
            # 階級降格リスクチェック
            grade_risk = self.check_grade_risk(student)
            if grade_risk:
                grade_risk_count += 1
                if not dry_run:
                    Alert.create_grade_risk_alert(
                        user=student,
                        current_grade=grade_risk['current_grade'],
                        risk_grade=grade_risk['risk_grade'],
                        days_behind=grade_risk['days_behind']
                    )
                    self.stdout.write(f'🚨 階級降格リスク: {student.username} - {grade_risk["days_behind"]}日遅れ')
                else:
                    self.stdout.write(f'[DRY RUN] 🚨 階級降格リスク: {student.username} - {grade_risk["days_behind"]}日遅れ')
            
            # 日報未提出チェック
            no_report_days = self.check_no_report(student)
            if no_report_days >= 3:  # 3日以上未提出
                no_report_count += 1
                if not dry_run:
                    Alert.create_no_report_alert(
                        user=student,
                        days_missing=no_report_days
                    )
                    self.stdout.write(f'📝 日報未提出: {student.username} - {no_report_days}日間')
                else:
                    self.stdout.write(f'[DRY RUN] 📝 日報未提出: {student.username} - {no_report_days}日間')
        
        # 解決済みチェック（アラートが解決されたものを自動的に無効化）
        resolved_count = self.check_resolved_alerts(dry_run)
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ アラートチェック完了: {timezone.now()}')
        )
        self.stdout.write(f'📊 階級降格リスク: {grade_risk_count}件')
        self.stdout.write(f'📊 日報未提出: {no_report_count}件')
        self.stdout.write(f'📊 解決済み: {resolved_count}件')

    def check_grade_risk(self, student):
        """階級降格リスクをチェック"""
        if not student.stats or not student.start_date:
            return None
        
        # 現在の日数と期待される進捗
        days_elapsed = (date.today() - student.start_date).days + 1
        current_grade = student.stats.current_grade
        current_phase = student.stats.current_phase
        
        if not current_phase:
            return None
        
        # 各階級の期待進度率
        grade_rates = {
            'S': 1.2,  # 120%
            'A': 1.0,  # 100%
            'B': 0.8,  # 80%
            'C': 0.6,  # 60%
            'D': 0.4,  # 40%
        }
        
        # 現在の進捗率を計算
        expected_day = days_elapsed * grade_rates.get(current_grade, 1.0)
        actual_day = current_phase.end_day if current_phase else 0
        
        days_behind = max(0, expected_day - actual_day)
        
        # 降格リスクの判定
        if days_behind >= 7:  # 7日以上遅れ
            # 次の階級を決定
            grade_order = ['S', 'A', 'B', 'C', 'D']
            current_index = grade_order.index(current_grade)
            if current_index < len(grade_order) - 1:
                risk_grade = grade_order[current_index + 1]
                return {
                    'current_grade': current_grade,
                    'risk_grade': risk_grade,
                    'days_behind': int(days_behind)
                }
        
        return None

    def check_no_report(self, student):
        """日報未提出日数をチェック"""
        # 最新の日報提出日を取得
        latest_report = DailyProgress.objects.filter(
            user=student
        ).aggregate(
            latest_date=Max('date')
        )['latest_date']
        
        if not latest_report:
            # 一度も日報を提出していない場合、研修開始日からの日数
            if student.start_date:
                return (date.today() - student.start_date).days + 1
            return 0
        
        # 最新の日報から今日までの日数
        days_since_report = (date.today() - latest_report).days
        return days_since_report

    def check_resolved_alerts(self, dry_run):
        """解決済みアラートをチェック"""
        resolved_count = 0
        
        # 階級降格リスクが解決されたアラートをチェック
        grade_risk_alerts = Alert.objects.filter(
            alert_type='grade_risk',
            is_active=True,
            is_resolved=False
        )
        
        for alert in grade_risk_alerts:
            grade_risk = self.check_grade_risk(alert.user)
            if not grade_risk:  # リスクが解消された
                resolved_count += 1
                if not dry_run:
                    alert.resolve()
                    self.stdout.write(f'✅ 階級降格リスク解消: {alert.user.username}')
                else:
                    self.stdout.write(f'[DRY RUN] ✅ 階級降格リスク解消: {alert.user.username}')
        
        # 日報未提出が解決されたアラートをチェック
        no_report_alerts = Alert.objects.filter(
            alert_type='no_report',
            is_active=True,
            is_resolved=False
        )
        
        for alert in no_report_alerts:
            no_report_days = self.check_no_report(alert.user)
            if no_report_days < 3:  # 3日未満なら解決
                resolved_count += 1
                if not dry_run:
                    alert.resolve()
                    self.stdout.write(f'✅ 日報未提出解消: {alert.user.username}')
                else:
                    self.stdout.write(f'[DRY RUN] ✅ 日報未提出解消: {alert.user.username}')
        
        return resolved_count