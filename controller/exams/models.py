from django.db import models
from django.conf import settings

class Exam(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_exams'
    )
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.PositiveIntegerField(default=60,help_text="Duração em minutos")
    max_attempts = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} (ID: {self.id})"

class Question(models.Model):
    TYPE_CHOICES = [
        ('MCQ', 'Múltipla Escolha'),
        ('TF', 'Verdadeiro/Falso'),
        ('SA', 'Resposta Curta'),
    ]

    exam = models.ForeignKey(Exam, related_name='questions', on_delete=models.CASCADE)
    text = models.TextField()
    question_type = models.CharField(max_length=3, choices=TYPE_CHOICES, default='MCQ')
    points = models.PositiveIntegerField(default=1)
    explanation = models.TextField(blank=True)

class Choice(models.Model):
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

class Participant(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='exam_participations'
    )
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='participants')
    score = models.FloatField(default=0)
    rank = models.PositiveIntegerField(null=True, blank=True)
    current_attempt = models.PositiveIntegerField(default=1)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'exam', 'current_attempt')
    
    def update_rank(sender, instance, **kwargs):
        participants = Participant.objects.filter(exam=instance.exam).order_by('-score')
        for index, participant in enumerate(participants, start=1):
            participant.rank = index
            participant.save()

class Answer(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE, null=True, blank=True)
    text_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(default=False)
    response_time = models.PositiveIntegerField(default=0,  # Adicione um valor padrão
        help_text="Tempo de resposta em segundos")
    answered_at = models.DateTimeField(auto_now_add=True)