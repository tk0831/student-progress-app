from django import forms
from ..models import CustomUser, Group


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