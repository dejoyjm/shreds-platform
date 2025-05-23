# Generated by Django 5.1.7 on 2025-04-02 18:05

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('test_engine', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuestionCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='testsectionconfig',
            name='num_easy',
        ),
        migrations.RemoveField(
            model_name='testsectionconfig',
            name='num_hard',
        ),
        migrations.RemoveField(
            model_name='testsectionconfig',
            name='num_moderate',
        ),
        migrations.RemoveField(
            model_name='testsectionconfig',
            name='section_name',
        ),
        migrations.AddField(
            model_name='testsectionconfig',
            name='easy_questions',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='testsectionconfig',
            name='hard_questions',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='testsectionconfig',
            name='moderate_questions',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='testsectionconfig',
            name='section_duration_minutes',
            field=models.PositiveIntegerField(default=10),
        ),
        migrations.AlterField(
            model_name='testsectionconfig',
            name='test',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='test_engine.test'),
        ),
        migrations.AlterField(
            model_name='question',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='test_engine.questioncategory'),
        ),
        migrations.AlterField(
            model_name='testsectionconfig',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='test_engine.questioncategory'),
        ),
    ]
