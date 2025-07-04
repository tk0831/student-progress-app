from django import forms
from django.utils import timezone
from ..models import CustomUser, Group, Phase, CurriculumItem, DailyProgress


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


class UserTrainingEditForm(forms.Form):
    """システム管理者用研修詳細編集フォーム"""
    start_date = forms.DateField(
        label='研修開始日',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
        }),
        required=False
    )
    
    current_phase = forms.ModelChoiceField(
        label='現在のPhase',
        queryset=Phase.objects.all(),
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
        })
    )
    
    current_item = forms.ModelChoiceField(
        label='現在の項目',
        queryset=CurriculumItem.objects.all(),
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
        }),
        required=False
    )
    
    days_elapsed = forms.IntegerField(
        label='経過日数',
        widget=forms.NumberInput(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
            'min': '0'
        }),
        min_value=0,
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # ユーザーの現在情報を初期値として設定
            self.fields['start_date'].initial = user.start_date
            
            # 最新の進捗から現在のPhaseと項目を取得
            latest_progress = DailyProgress.objects.filter(user=user).order_by('-date').first()
            if latest_progress:
                self.fields['current_phase'].initial = latest_progress.current_phase
                self.fields['current_item'].initial = latest_progress.current_item
                self.fields['days_elapsed'].initial = latest_progress.days_elapsed
                
                # 現在のPhaseに基づいて項目をフィルタリング
                if latest_progress.current_phase:
                    self.fields['current_item'].queryset = CurriculumItem.objects.filter(
                        phase=latest_progress.current_phase
                    )
    
    def clean(self):
        cleaned_data = super().clean()
        current_phase = cleaned_data.get('current_phase')
        current_item = cleaned_data.get('current_item')
        
        # 選択された項目が選択されたPhaseに属しているか確認
        if current_phase and current_item:
            if current_item.phase != current_phase:
                raise forms.ValidationError(
                    f'選択された項目「{current_item}」は、選択されたPhase「{current_phase}」に属していません。'
                )
        
        return cleaned_data


class ItemProgressEditForm(forms.ModelForm):
    """個別項目の進捗編集フォーム"""
    class Meta:
        model = DailyProgress
        fields = ['date', 'current_phase', 'current_item', 'study_hours', 'days_elapsed', 'item_completed']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'current_phase': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'current_item': forms.Select(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            }),
            'study_hours': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'step': '0.5',
                'min': '0'
            }),
            'days_elapsed': forms.NumberInput(attrs={
                'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500',
                'min': '0'
            }),
            'item_completed': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-blue-600 focus:ring-blue-500'
            })
        }
        labels = {
            'date': '記録日',
            'current_phase': 'Phase',
            'current_item': '項目',
            'study_hours': '学習時間',
            'days_elapsed': '経過日数',
            'item_completed': '項目完了'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Phaseが選択されている場合、そのPhaseの項目のみ表示
        if self.instance and self.instance.current_phase:
            self.fields['current_item'].queryset = CurriculumItem.objects.filter(
                phase=self.instance.current_phase
            )