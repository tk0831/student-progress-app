from django.db import models
from datetime import date, timedelta
from .user import CustomUser
from .curriculum import Phase, CurriculumItem
from .progress import DailyProgress


class UserStats(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='stats')
    total_study_hours = models.DecimalField(max_digits=7, decimal_places=1, default=0, verbose_name='累計学習時間')
    current_phase = models.ForeignKey(Phase, on_delete=models.CASCADE, null=True, verbose_name='現在のPhase')
    current_item = models.ForeignKey(CurriculumItem, on_delete=models.CASCADE, null=True, verbose_name='現在の項目')
    current_grade = models.CharField(max_length=1, choices=DailyProgress.GRADE_CHOICES, default='A', verbose_name='現在の階級')
    days_elapsed = models.IntegerField(default=0, verbose_name='経過日数')
    delay_days = models.IntegerField(default=0, verbose_name='遅れ日数')
    stars = models.IntegerField(default=0, verbose_name='星の数')
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='完了率')
    efficiency_score = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name='進捗効率スコア')
    estimated_completion_date = models.DateField(null=True, blank=True, verbose_name='完了見込み日')
    last_updated = models.DateTimeField(auto_now=True)
    
    def calculate_progress_status(self):
        """進捗状況を計算"""
        if not self.user.start_date or not self.current_phase or not self.current_item:
            return None
            
        # 実際の経過日数
        actual_days = (date.today() - self.user.start_date).days + 1
        
        # 現在の項目までの標準日数を計算（Null項目を除外）
        items_before = CurriculumItem.objects.filter(
            phase__phase_number__lt=self.current_phase.phase_number,
            estimated_days__isnull=False
        ).aggregate(total_days=models.Sum('estimated_days'))['total_days'] or 0
        
        items_in_phase = CurriculumItem.objects.filter(
            phase=self.current_phase,
            estimated_days__isnull=False,
            order__lte=self.current_item.order
        ).aggregate(total_days=models.Sum('estimated_days'))['total_days'] or 0
        
        expected_days = items_before + items_in_phase
        
        # 遅れ日数計算: 期待日数 - 実際経過日数 = 遅れ日数
        # プラス = 進行中（予定より早い）, マイナス = 遅れ（予定より遅い）
        delay_days = expected_days - actual_days
        
        return {
            'actual_days': actual_days,
            'expected_days': expected_days,
            'delay_days': delay_days,
            'is_ahead': delay_days > 2,      # 2日以上進行中
            'is_on_track': abs(delay_days) <= 2,  # ±2日以内で順調
            'is_behind': delay_days < -2,    # 2日以上遅れ
            'progress_percentage': min(100, (actual_days / max(expected_days, 1)) * 100)
        }
    
    def calculate_completion_rate(self):
        """完了率を計算（完了項目数 / 全項目数 × 100）"""
        if not self.current_phase or not self.current_item:
            return 0
        
        # 全カリキュラム項目数
        total_items = CurriculumItem.objects.count()
        if total_items == 0:
            return 0
        
        # 完了項目数を計算
        completed_items = 0
        
        # 前のPhaseの全項目
        before_phases_items = CurriculumItem.objects.filter(
            phase__phase_number__lt=self.current_phase.phase_number
        ).count()
        completed_items += before_phases_items
        
        # 現在Phaseの現在項目まで
        current_phase_items = CurriculumItem.objects.filter(
            phase=self.current_phase,
            order__lte=self.current_item.order
        ).count()
        completed_items += current_phase_items
        
        # 完了率計算: (完了項目数 / 全項目数) × 100
        return round((completed_items / total_items) * 100, 2)
    
    def update_completion_rate(self):
        """完了率を再計算して更新"""
        self.completion_rate = self.calculate_completion_rate()
        self.save()
    
    def calculate_efficiency_score(self):
        """進捗効率スコアを計算"""
        if not self.user.start_date:
            return 0
        
        # 現在の完了率
        completion_rate = self.calculate_completion_rate()
        if completion_rate == 0:
            return 0
        
        # 経過日数
        days_elapsed = (date.today() - self.user.start_date).days + 1
        
        # 期待進捗率（150日で100%完了が標準）
        expected_days = 150
        expected_completion_rate = min((days_elapsed / expected_days) * 100, 100)
        
        if expected_completion_rate == 0:
            return 0
        
        # 進捗効率スコア = (実際の完了率 / 期待完了率) × 100
        efficiency_score = (completion_rate / expected_completion_rate) * 100
        
        return round(efficiency_score, 2)
    
    def update_efficiency_score(self):
        """進捗効率スコアを再計算して更新"""
        self.efficiency_score = self.calculate_efficiency_score()
        self.save()
    
    def calculate_grade_from_days(self):
        """日数ベースで階級を計算（現在項目までの期待日数 vs 経過日数）"""
        if not self.user.start_date or not self.current_phase or not self.current_item:
            return 'D'
        
        # 実際の経過日数
        actual_days = (date.today() - self.user.start_date).days + 1
        
        # 現在項目までの期待日数を計算
        items_before = CurriculumItem.objects.filter(
            phase__phase_number__lt=self.current_phase.phase_number
        ).aggregate(total_days=models.Sum('estimated_days'))['total_days'] or 0
        
        items_in_phase = CurriculumItem.objects.filter(
            phase=self.current_phase,
            order__lte=self.current_item.order
        ).aggregate(total_days=models.Sum('estimated_days'))['total_days'] or 0
        
        expected_days = items_before + items_in_phase
        
        if expected_days == 0:
            return 'D'
        
        # 進捗比率を計算: 期待日数 / 実際経過日数
        progress_ratio = expected_days / actual_days
        
        # 階級判定
        if progress_ratio >= 1.2:      # 期待の120%以上の速度（大幅先行）
            return 'S'
        elif progress_ratio >= 1.0:    # 期待通りかそれ以上の速度
            return 'A'
        elif progress_ratio >= 0.8:    # 期待の80%以上の速度
            return 'B'
        elif progress_ratio >= 0.6:    # 期待の60%以上の速度
            return 'C'
        else:                          # 期待の60%未満の速度
            return 'D'
    
    def calculate_grade_from_efficiency(self):
        """進捗効率スコアから階級を計算（旧メソッド - 非推奨）"""
        # 新しい日数ベース計算を使用
        return self.calculate_grade_from_days()
    
    def update_delay_status(self):
        """遅れ状態を計算して更新"""
        progress_status = self.calculate_progress_status()
        if progress_status:
            # delay_daysはプラス=進行中、マイナス=遅れ として保存
            self.delay_days = progress_status['delay_days']
            self.days_elapsed = progress_status['actual_days']
            self.save(update_fields=['delay_days', 'days_elapsed'])
    
    def update_all_stats(self):
        """すべての統計情報を一括更新"""
        # 完了率更新
        self.completion_rate = self.calculate_completion_rate()
        
        # 効率スコア更新
        self.efficiency_score = self.calculate_efficiency_score()
        
        # 階級更新（日数ベース）
        self.current_grade = self.calculate_grade_from_days()
        
        # 遅れ状態更新
        progress_status = self.calculate_progress_status()
        if progress_status:
            self.delay_days = progress_status['delay_days']
            self.days_elapsed = progress_status['actual_days']
        
        self.save()
    
    @property
    def progress_status_display(self):
        """進捗状況の表示用文字列"""
        status = self.calculate_progress_status()
        if not status:
            return '不明'
        
        if status['is_ahead']:
            return f"進行中（+{status['delay_days']}日先行）"
        elif status['is_on_track']:
            return "順調"
        elif status['is_behind']:
            return f"遅れ気味（{abs(status['delay_days'])}日遅れ）"
        else:
            return "順調"
    
    def calculate_grade_change_prediction(self):
        """階級変更予測を計算"""
        if not self.user.start_date or not self.current_phase or not self.current_item:
            return None
            
        current_grade = self.current_grade
        grade_order = ['D', 'C', 'B', 'A', 'S']
        
        # 次の階級を取得
        current_index = grade_order.index(current_grade) if current_grade in grade_order else 0
        
        prediction_data = {
            'current_grade': current_grade,
            'next_grade': None,
            'days_to_complete_current': None,
            'is_current_item_sufficient': False,
            'next_milestone': None,
            'completion_percentage': None
        }
        
        # 現在の進捗状況
        actual_days = (date.today() - self.user.start_date).days + 1
        
        # 現在項目までの期待日数
        items_before = CurriculumItem.objects.filter(
            phase__phase_number__lt=self.current_phase.phase_number
        ).aggregate(total_days=models.Sum('estimated_days'))['total_days'] or 0
        
        items_in_phase_before = CurriculumItem.objects.filter(
            phase=self.current_phase,
            order__lt=self.current_item.order
        ).aggregate(total_days=models.Sum('estimated_days'))['total_days'] or 0
        
        current_item_days = self.current_item.estimated_days or 1
        current_expected_days_before_item = items_before + items_in_phase_before
        current_expected_days_with_item = current_expected_days_before_item + current_item_days
        
        # 階級境界値
        grade_thresholds = {
            'S': 1.2,  # 120%以上
            'A': 1.0,  # 100%以上
            'B': 0.8,  # 80%以上
            'C': 0.6,  # 60%以上
            'D': 0.0   # 60%未満
        }
        
        # 上位階級への昇格可能性をチェック
        if current_index < len(grade_order) - 1:
            next_grade = grade_order[current_index + 1]
            required_ratio = grade_thresholds[next_grade]
            
            # 次の階級に必要な期待日数を計算
            required_expected_days = actual_days * required_ratio
            
            # 現在の項目を完了することで条件を満たすかチェック
            if current_expected_days_with_item >= required_expected_days:
                # 現在の項目完了で昇格可能
                days_remaining = current_item_days - (actual_days - current_expected_days_before_item - 1)
                days_remaining = max(1, days_remaining)  # 最低1日
                
                prediction_data.update({
                    'next_grade': next_grade,
                    'days_to_complete_current': int(days_remaining),
                    'is_current_item_sufficient': True,
                    'next_milestone': f"{self.current_item.item_code}: {self.current_item.name}",
                    'completion_percentage': round((current_expected_days_before_item / required_expected_days) * 100, 1)
                })
            else:
                # 現在の項目だけでは不足、追加項目が必要
                days_needed = required_expected_days - current_expected_days_with_item
                
                # 次の項目を取得
                next_items = CurriculumItem.objects.filter(
                    models.Q(phase=self.current_phase, order__gt=self.current_item.order) |
                    models.Q(phase__phase_number__gt=self.current_phase.phase_number)
                ).order_by('phase__phase_number', 'order')
                
                accumulated_days = 0
                target_item = None
                
                for item in next_items:
                    item_days = item.estimated_days or 1
                    accumulated_days += item_days
                    if accumulated_days >= days_needed:
                        target_item = item
                        break
                
                if target_item:
                    total_days_needed = current_item_days + accumulated_days - (actual_days - current_expected_days_before_item - 1)
                    total_days_needed = max(1, total_days_needed)
                    
                    prediction_data.update({
                        'next_grade': next_grade,
                        'days_to_complete_current': int(total_days_needed),
                        'is_current_item_sufficient': False,
                        'next_milestone': f"{target_item.item_code}: {target_item.name}",
                        'completion_percentage': round((current_expected_days_before_item / required_expected_days) * 100, 1)
                    })
        
        return prediction_data
    
    @property
    def grade_change_prediction(self):
        """階級変更予測のプロパティ"""
        return self.calculate_grade_change_prediction()
    
    @property
    def progress_status_class(self):
        """進捗状況のCSSクラス"""
        status = self.calculate_progress_status()
        if not status:
            return 'text-gray-500'
        
        if status['is_ahead']:
            return 'text-blue-600'
        elif status['is_on_track']:
            return 'text-green-600'
        elif status['is_behind']:
            return 'text-red-600'
        else:
            return 'text-gray-600'
    
    def calculate_graduation_estimate(self):
        """卒業見込み月と信頼度を計算"""
        if not self.user.start_date or not self.current_phase or not self.current_item:
            return None
            
        from django.db.models import Avg, StdDev, Sum
        import calendar
        
        # 現在までの実際の経過日数
        days_elapsed = (date.today() - self.user.start_date).days + 1
        
        # 現在の項目までの期待日数を計算
        completed_days = 0
        
        # 前のPhaseの全項目日数
        before_phases_days = CurriculumItem.objects.filter(
            phase__phase_number__lt=self.current_phase.phase_number,
            estimated_days__isnull=False
        ).aggregate(total=Sum('estimated_days'))['total'] or 0
        
        # 現在Phaseの現在項目までの日数
        current_phase_days = CurriculumItem.objects.filter(
            phase=self.current_phase,
            order__lte=self.current_item.order,
            estimated_days__isnull=False
        ).aggregate(total=Sum('estimated_days'))['total'] or 0
        
        completed_days = before_phases_days + current_phase_days
        
        # 残りの項目の期待日数を計算
        remaining_days = 0
        
        # 現在Phaseの残り項目
        current_phase_remaining = CurriculumItem.objects.filter(
            phase=self.current_phase,
            order__gt=self.current_item.order,
            estimated_days__isnull=False
        ).aggregate(total=Sum('estimated_days'))['total'] or 0
        
        # 今後のPhaseの全項目
        future_phases_days = CurriculumItem.objects.filter(
            phase__phase_number__gt=self.current_phase.phase_number,
            estimated_days__isnull=False
        ).aggregate(total=Sum('estimated_days'))['total'] or 0
        
        remaining_days = current_phase_remaining + future_phases_days
        
        # 現在の進捗ペースを計算（実際日数 vs 期待日数）
        if completed_days <= 0:
            return None
            
        # ペース比率: 1.0 = 予定通り, 0.8 = 遅れ気味, 1.2 = 早い
        pace_ratio = completed_days / days_elapsed if days_elapsed > 0 else 1.0
        
        # 残り日数をペース比率で調整して推定
        estimated_remaining_days = remaining_days / pace_ratio if pace_ratio > 0 else remaining_days * 1.5
        
        # 卒業見込み日を計算
        estimated_completion_date = date.today() + timedelta(days=int(estimated_remaining_days))
        
        # 過去30日間の学習時間の安定性を計算
        recent_progress = DailyProgress.objects.filter(
            user=self.user,
            date__gte=date.today() - timedelta(days=30)
        ).order_by('-date')
        
        if recent_progress.count() < 10:  # データが少ない場合
            reliability = 'low'
        else:
            # 学習時間の平均と標準偏差を計算
            stats = recent_progress.aggregate(
                avg_hours=Avg('study_hours'),
                std_hours=StdDev('study_hours')
            )
            
            avg_hours = stats['avg_hours'] or 0
            std_hours = stats['std_hours'] or 0
            
            # 継続性を確認（記録日数の割合）
            expected_days = min(30, days_elapsed)
            recording_rate = recent_progress.count() / expected_days if expected_days > 0 else 0
            
            # 安定性の判定
            if avg_hours > 0:
                variation_coefficient = std_hours / avg_hours  # 変動係数
            else:
                variation_coefficient = 1.0
            
            # 信頼度の計算
            # - 記録率が80%以上
            # - 変動係数が0.5以下（安定している）
            # - 平均学習時間が2時間以上
            if (recording_rate >= 0.8 and 
                variation_coefficient <= 0.5 and 
                avg_hours >= 2.0):
                reliability = 'high'
            elif (recording_rate >= 0.6 and 
                  variation_coefficient <= 0.8 and 
                  avg_hours >= 1.5):
                reliability = 'medium'
            else:
                reliability = 'low'
        
        return {
            'estimated_completion_date': estimated_completion_date,
            'estimated_month': estimated_completion_date.strftime('%Y年%m月'),
            'month_name': f"{estimated_completion_date.year}年{estimated_completion_date.month}月",
            'reliability': reliability,
            'reliability_display': {
                'high': '卒業見込み高',
                'medium': '卒業見込み中',
                'low': '卒業見込み低'
            }[reliability],
            'days_remaining': max(0, int(estimated_remaining_days)),
            'completed_days': completed_days,
            'remaining_days': remaining_days,
            'pace_ratio': round(pace_ratio, 2),
            'total_expected_days': completed_days + remaining_days
        }
    
    @property
    def graduation_estimate_display(self):
        """卒業見込みの表示用文字列"""
        estimate = self.calculate_graduation_estimate()
        if not estimate:
            return '見込み算出不可'
            
        return f"{estimate['month_name']} {estimate['reliability_display']}"
    
    class Meta:
        verbose_name = 'ユーザー統計'
        verbose_name_plural = 'ユーザー統計'


class WeeklyRanking(models.Model):
    """週間ランキング記録"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='weekly_rankings')
    week_start = models.DateField(verbose_name='週開始日')  # 月曜日
    week_end = models.DateField(verbose_name='週終了日')    # 日曜日
    rank = models.IntegerField(verbose_name='順位')
    completed_standard_days = models.IntegerField(verbose_name='完了項目標準日数合計')
    efficiency_score = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='進捗効率スコア')
    total_study_hours = models.DecimalField(max_digits=6, decimal_places=1, verbose_name='総学習時間')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = '週間ランキング'
        verbose_name_plural = '週間ランキング'
        unique_together = ['user', 'week_start']
        ordering = ['-week_start', 'rank']
    
    def __str__(self):
        return f"{self.user.username} - {self.week_start}週 - {self.rank}位"