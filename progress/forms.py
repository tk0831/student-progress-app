from django import forms
from .models import DailyProgress, Phase, CurriculumItem


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
            'problem_detail', 'tried_solutions', 'reflection',
            'next_goal', 'next_phase', 'next_item', 'planned_hours',
            'action_plan', 'need_review', 'have_question', 'next_phase_ready'
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
                'placeholder': '明日の学習目標を記入してください（200文字以内・必須）'
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
            'reflection': '今日の振り返り・反省点',
            'next_goal': '明日の目標',
            'next_phase': '予定Phase',
            'next_item': '予定項目',
            'planned_hours': '予定学習時間（時間）',
            'action_plan': '具体的な行動計画',
            'need_review': '復習必要',
            'have_question': '質問予定',
            'next_phase_ready': '次Phase進行予定',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
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
                self.fields['current_item'].queryset = CurriculumItem.objects.filter(phase_id=phase_id)
            except (ValueError, TypeError):
                self.fields['current_item'].queryset = CurriculumItem.objects.none()
        elif self.instance.pk and self.instance.current_phase:
            self.fields['current_item'].queryset = CurriculumItem.objects.filter(phase=self.instance.current_phase)
        else:
            self.fields['current_item'].queryset = CurriculumItem.objects.none()
        
        # 予定Phaseに基づいて予定項目をフィルタリング
        if 'next_phase' in self.data:
            try:
                phase_id = int(self.data.get('next_phase'))
                self.fields['next_item'].queryset = CurriculumItem.objects.filter(phase_id=phase_id)
            except (ValueError, TypeError):
                self.fields['next_item'].queryset = CurriculumItem.objects.none()
        elif self.instance.pk and self.instance.next_phase:
            self.fields['next_item'].queryset = CurriculumItem.objects.filter(phase=self.instance.next_phase)
        else:
            self.fields['next_item'].queryset = CurriculumItem.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        feedback_requested = cleaned_data.get('feedback_requested')
        problem_detail = cleaned_data.get('problem_detail')
        tried_solutions = cleaned_data.get('tried_solutions')
        
        # フィードバック希望時の必須チェック
        if feedback_requested:
            if not problem_detail:
                raise forms.ValidationError('フィードバック希望時は具体的な問題内容の入力が必須です。')
            if not tried_solutions:
                raise forms.ValidationError('フィードバック希望時は試したことの入力が必須です。')
        
        return cleaned_data