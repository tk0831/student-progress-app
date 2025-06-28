from django import forms
from ..models import Group


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