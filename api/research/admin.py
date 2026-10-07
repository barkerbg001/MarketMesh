from django.contrib import admin

from research.models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ("created_at", "role", "agent", "status", "content")
    readonly_fields = fields
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("title", "updated_at", "created_at")
    search_fields = ("title",)
    readonly_fields = ("id", "created_at", "updated_at", "research_context")
    inlines = [MessageInline]
