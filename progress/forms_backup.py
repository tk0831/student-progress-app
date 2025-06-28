from django import forms
from .models import DailyProgress, Phase, CurriculumItem, Group, CustomUser


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ユーザー名'
        }),
        label='ユーザー名'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'パスワード'
        }),
        label='パスワード'
    )


class DailyProgressForm(forms.ModelForm):
    class Meta:
        model = DailyProgress
        fields = [
            'current_phase', 'current_item', 'progress_detail',
            'study_hours', 'stuck_content', 'feedback_requested',
            'problem_detail', 'tried_solutions', 'attachment_file', 'reflection',
            'next_phase', 'next_item', 'planned_hours', 'next_goal',
            'action_plan', 'need_review', 'have_question', 'next_phase_ready',
            'item_completed'
        ]
        widgets = {
            'current_phase': forms.Select(attrs={'class': 'form-control'}),
            'current_item': forms.Select(attrs={'class': 'form-control'}),
            'progress_detail': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'maxlength': 100,
                'placeholder': '現在の進捗状況を簡潔に記入してください（100文字以内・任意）'
            }),
            'study_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0'
            }),
            'stuck_content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'maxlength': 500,
                'placeholder': '詰まった内容があれば記入してください（500文字以内・任意）'
            }),
            'feedback_requested': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'problem_detail': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'maxlength': 300,
                'placeholder': 'フィードバック希望時は具体的な問題内容を記入（300文字以内）'
            }),
            'tried_solutions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'maxlength': 300,
                'placeholder': 'フィードバック希望時は試したことを記入（300文字以内）'
            }),
            'attachment_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.zip',
                'data-file-types': 'ZIP'
            }),
            'reflection': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'maxlength': 300,
                'placeholder': '今日の学習を振り返って感じたことを記入してください（300文字以内・必須）'
            }),
            'next_goal': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'maxlength': 200,
                'placeholder': '明日の学習目標を記入してください（200文字以内・任意）'
            }),
            'next_phase': forms.Select(attrs={'class': 'form-control'}),
            'next_item': forms.Select(attrs={'class': 'form-control'}),
            'planned_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0'
            }),
            'action_plan': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'maxlength': 200,
                'placeholder': '明日の具体的な行動計画を記入してください（200文字以内・必須）'
            }),
            'need_review': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'have_question': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'next_phase_ready': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'item_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'current_phase': '現在のPhase',
            'current_item': '現在の項目',
            'progress_detail': '進捗詳細',
            'study_hours': '本日の学習時間（時間）',
            'stuck_content': '詰まったポイント',
            'feedback_requested': 'フィードバック希望',
            'problem_detail': '具体的な問題内容',
            'tried_solutions': '試したこと',
            'attachment_file': '添付ファイル（ZIP）',
            'reflection': '今日の振り返り・反省点',
            'next_goal': '明日の目標（任意）',
            'next_phase': '予定Phase',
            'next_item': '予定項目',
            'planned_hours': '予定学習時間（時間）',
            'action_plan': '具体的な行動計画',
            'need_review': '復習必要',
            'have_question': '質問予定',
            'next_phase_ready': '次Phase進行予定',
            'item_completed': '項目完了',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # next_goalを任意にする
        self.fields['next_goal'].required = False
        
        # ユーザーの進捗状況に基づいてフィールドをフィルタリング
        if self.user and self.user.user_type == 'student':
            progress_status = self.user.get_current_progress_status()
            if progress_status:
                # 利用可能なフェーズのみ表示
                self.fields['current_phase'].queryset = progress_status['available_phases']
                self.fields['next_phase'].queryset = progress_status['available_phases']
        
        # フィードバック関連フィールドの表示制御
        if 'feedback_requested' in self.data:
            # フィードバック希望がチェックされている場合、関連フィールドを必須にする
            if self.data.get('feedback_requested'):
                self.fields['problem_detail'].required = True
                self.fields['tried_solutions'].required = True
        
        # 現在のPhaseに基づいて項目をフィルタリング
        if 'current_phase' in self.data:
            try:
                phase_id = int(self.data.get('current_phase'))
                self.fields['current_item'].queryset = CurriculumItem.objects.filter(phase_id=phase_id).order_by('order')
            except (ValueError, TypeError):
                self.fields['current_item'].queryset = CurriculumItem.objects.none()
        elif self.instance.pk and self.instance.current_phase:
            self.fields['current_item'].queryset = CurriculumItem.objects.filter(phase=self.instance.current_phase).order_by('order')
        else:
            # 初期表示時は全ての項目を表示（JavaScriptが動的に絞り込む）
            self.fields['current_item'].queryset = CurriculumItem.objects.all().order_by('phase__phase_number', 'order')
        
        # 予定Phaseに基づいて予定項目をフィルタリング
        if 'next_phase' in self.data:
            try:
                phase_id = int(self.data.get('next_phase'))
                self.fields['next_item'].queryset = CurriculumItem.objects.filter(phase_id=phase_id).order_by('order')
            except (ValueError, TypeError):
                self.fields['next_item'].queryset = CurriculumItem.objects.none()
        elif self.instance.pk and self.instance.next_phase:
            self.fields['next_item'].queryset = CurriculumItem.objects.filter(phase=self.instance.next_phase).order_by('order')
        else:
            # 初期表示時は全ての項目を表示（JavaScriptが動的に絞り込む）
            self.fields['next_item'].queryset = CurriculumItem.objects.all().order_by('phase__phase_number', 'order')

    def clean(self):
        cleaned_data = super().clean()
        feedback_requested = cleaned_data.get('feedback_requested')
        problem_detail = cleaned_data.get('problem_detail')
        tried_solutions = cleaned_data.get('tried_solutions')
        current_phase = cleaned_data.get('current_phase')
        current_item = cleaned_data.get('current_item')
        next_phase = cleaned_data.get('next_phase')
        next_item = cleaned_data.get('next_item')
        
        # フィードバック希望時の必須チェック
        if feedback_requested:
            if not problem_detail:
                raise forms.ValidationError('フィードバック希望時は具体的な問題内容の入力が必須です。')
            if not tried_solutions:
                raise forms.ValidationError('フィードバック希望時は試したことの入力が必須です。')
        
        # 進捗バリデーション（研修生のみ）
        if self.user and self.user.user_type == 'student':
            progress_status = self.user.get_current_progress_status()
            if progress_status:
                available_phase_ids = list(progress_status['available_phases'].values_list('id', flat=True))
                
                # 現在のフェーズチェック
                if current_phase and current_phase.id not in available_phase_ids:
                    raise forms.ValidationError(f'フェーズ「{current_phase.name}」は選択できません。完了済みのフェーズです。')
                
                # 現在の項目チェック
                if current_item and current_phase:
                    if current_item.phase != current_phase:
                        raise forms.ValidationError('選択された項目は現在のフェーズに属していません。')
                
                # 予定フェーズチェック
                if next_phase and next_phase.id not in available_phase_ids:
                    raise forms.ValidationError(f'予定フェーズ「{next_phase.name}」は選択できません。完了済みのフェーズです。')
                
                # 予定項目チェック
                if next_item and next_phase:
                    if next_item.phase != next_phase:
                        raise forms.ValidationError('選択された予定項目は予定フェーズに属していません。')
        
        # ファイルバリデーション
        attachment_file = cleaned_data.get('attachment_file')
        if attachment_file:
            # ファイルサイズチェック（50MB制限）
            if attachment_file.size > 50 * 1024 * 1024:
                raise forms.ValidationError('ファイルサイズは50MB以下にしてください。')
            
            # ファイル拡張子チェック
            import os
            file_name = attachment_file.name.lower()
            if not file_name.endswith('.zip'):
                raise forms.ValidationError('ZIPファイルのみアップロード可能です。')
        
        return cleaned_data


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'グループ名を入力してください'
            }),
            'description': forms.Textarea(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'rows': 4,
                'placeholder': 'グループの説明を入力してください（任意）'
            }),
        }
        labels = {
            'name': 'グループ名',
            'description': 'グループ説明',
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            # 同名グループの存在チェック（編集時は自分自身を除外）
            existing_groups = Group.objects.filter(name=name)
            if self.instance.pk:
                existing_groups = existing_groups.exclude(pk=self.instance.pk)
            
            if existing_groups.exists():
                raise forms.ValidationError('このグループ名は既に使用されています。')
        
        return name


class UserGroupAssignForm(forms.ModelForm):
    """ユーザーのグループ割り当てフォーム"""
    students = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.filter(user_type='student'),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=False,
        label='グループメンバー'
    )
    
    class Meta:
        model = Group
        fields = ['students']
    
    def __init__(self, *args, **kwargs):
        group_instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        
        # 現在のグループメンバーを初期選択
        if group_instance:
            self.fields['students'].initial = group_instance.customuser_set.all()

    def save(self, commit=True):
        group = super().save(commit=commit)
        if commit:
            # 既存のグループメンバーをクリア
            group.customuser_set.clear()
            # 新しいメンバーを設定
            selected_students = self.cleaned_data['students']
            for student in selected_students:
                student.group = group
                student.save()
        return group


class UserRegistrationForm(forms.ModelForm):
    """新規ユーザー登録フォーム（誰でも登録可能）"""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'パスワードを入力してください'
        }),
        label='パスワード'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'パスワードを再入力してください'
        }),
        label='パスワード確認'
    )
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'start_date']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'ユーザー名を入力してください'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'メールアドレスを入力してください'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': '姓を入力してください'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': '名を入力してください'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'type': 'date'
            }),
        }
        labels = {
            'username': 'ユーザー名',
            'email': 'メールアドレス',
            'first_name': '姓',
            'last_name': '名',
            'start_date': '研修開始日',
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('パスワードが一致しません。')
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.user_type = 'student'  # 自動的に研修生として登録
        if commit:
            user.save()
        return user


class UserCreateForm(forms.ModelForm):
    """新規ユーザー作成フォーム"""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'パスワードを入力してください'
        }),
        label='パスワード'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'placeholder': 'パスワードを再入力してください'
        }),
        label='パスワード確認'
    )
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'user_type', 'group', 'start_date', 'assigned_admin']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'ユーザー名を入力してください'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': 'メールアドレスを入力してください'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': '姓を入力してください'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'placeholder': '名を入力してください'
            }),
            'user_type': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'group': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'type': 'date'
            }),
            'assigned_admin': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
        }
        labels = {
            'username': 'ユーザー名',
            'email': 'メールアドレス',
            'first_name': '姓',
            'last_name': '名',
            'user_type': 'ユーザータイプ',
            'group': 'グループ',
            'start_date': '研修開始日',
            'assigned_admin': '担当研修管理者',
        }

    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        
        # 担当研修管理者の選択肢を研修管理者のみに制限
        self.fields['assigned_admin'].queryset = CustomUser.objects.filter(user_type='training_admin')
        self.fields['assigned_admin'].required = False
        
        # システム管理者以外は担当者とユーザータイプを編集できないようにする
        if current_user and current_user.user_type != 'system_admin':
            self.fields['assigned_admin'].disabled = True
            self.fields['user_type'].disabled = True
            self.fields['user_type'].help_text = 'システム管理者のみ変更可能です'
            
        # ユーザータイプによって担当者フィールドの表示/非表示を制御
        self.fields['assigned_admin'].help_text = '研修生のみ設定可能です'

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('パスワードが一致しません。')
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user