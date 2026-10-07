import { useState } from 'react'
import { DownloadIcon, Loader2Icon, MessageSquarePlusIcon, MoreHorizontalIcon, PencilIcon, Trash2Icon } from 'lucide-react'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { routeHref } from '@/hooks/use-route'
import { timeAgo } from '@/lib/time'
import { cn } from '@/lib/utils'
import type { ConversationSummary } from '@/types/api'

type SidebarProps = {
  conversations: ConversationSummary[]
  loading: boolean
  error: string | null
  activeId: string | null
  onNew: () => void
  onRename: (conversation: ConversationSummary, title: string) => Promise<boolean>
  onDelete: (conversation: ConversationSummary) => Promise<void>
  onExport: (conversation: ConversationSummary, format: 'markdown' | 'json') => void
  onNavigate?: () => void
}

export function ConversationSidebar({
  conversations,
  loading,
  error,
  activeId,
  onNew,
  onRename,
  onDelete,
  onExport,
  onNavigate,
}: SidebarProps) {
  const [renaming, setRenaming] = useState<ConversationSummary | null>(null)
  const [title, setTitle] = useState('')
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState<ConversationSummary | null>(null)

  return (
    <nav aria-label="Conversations" className="flex h-full min-h-0 flex-col gap-2">
      <Button onClick={onNew} className="w-full justify-start">
        <MessageSquarePlusIcon data-icon="inline-start" aria-hidden="true" />
        New conversation
      </Button>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {loading && conversations.length === 0 ? (
          <div className="flex flex-col gap-2 p-1" aria-label="Loading conversations">
            {[0, 1, 2].map((index) => (
              <Skeleton key={index} className="h-10 w-full" />
            ))}
          </div>
        ) : error ? (
          <p className="p-2 text-sm text-destructive">{error}</p>
        ) : conversations.length === 0 ? (
          <p className="p-2 text-sm text-muted-foreground">No conversations yet. Your research will be saved here.</p>
        ) : (
          <ul className="flex flex-col gap-0.5">
            {conversations.map((conversation) => {
              const active = conversation.id === activeId
              return (
                <li key={conversation.id} className="group relative">
                  <a
                    href={routeHref({ view: 'chat', conversationId: conversation.id })}
                    onClick={onNavigate}
                    aria-current={active ? 'page' : undefined}
                    className={cn(
                      'flex flex-col rounded-md py-2 pr-9 pl-2.5 text-sm hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:outline-none',
                      active && 'bg-accent font-medium',
                    )}
                  >
                    <span className="flex items-center gap-1.5 truncate">
                      {conversation.running && (
                        <Loader2Icon className="size-3.5 shrink-0 animate-spin text-primary" aria-label="Working" />
                      )}
                      <span className="truncate">{conversation.title}</span>
                    </span>
                    <span className="text-xs font-normal text-muted-foreground">{timeAgo(conversation.updated_at)}</span>
                  </a>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        className="absolute top-1/2 right-1 -translate-y-1/2 opacity-100 sm:opacity-0 sm:group-focus-within:opacity-100 sm:group-hover:opacity-100 data-[state=open]:opacity-100"
                        aria-label={`Actions for ${conversation.title}`}
                      >
                        <MoreHorizontalIcon aria-hidden="true" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        onSelect={() => {
                          setTitle(conversation.title)
                          setRenaming(conversation)
                        }}
                      >
                        <PencilIcon aria-hidden="true" />
                        Rename
                      </DropdownMenuItem>
                      <DropdownMenuItem onSelect={() => onExport(conversation, 'markdown')}>
                        <DownloadIcon aria-hidden="true" />
                        Export as Markdown
                      </DropdownMenuItem>
                      <DropdownMenuItem onSelect={() => onExport(conversation, 'json')}>
                        <DownloadIcon aria-hidden="true" />
                        Export as JSON
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem variant="destructive" onSelect={() => setDeleting(conversation)}>
                        <Trash2Icon aria-hidden="true" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      <Dialog open={renaming !== null} onOpenChange={(open) => !open && setRenaming(null)}>
        <DialogContent>
          <form
            className="flex flex-col gap-4"
            onSubmit={async (event) => {
              event.preventDefault()
              if (!renaming || !title.trim()) return
              setSaving(true)
              const ok = await onRename(renaming, title.trim())
              setSaving(false)
              if (ok) setRenaming(null)
            }}
          >
            <DialogHeader>
              <DialogTitle>Rename conversation</DialogTitle>
              <DialogDescription>Give this research thread a name you will recognise later.</DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-2">
              <Label htmlFor="conversation-title">Title</Label>
              <Input
                id="conversation-title"
                value={title}
                maxLength={120}
                autoFocus
                onChange={(event) => setTitle(event.target.value)}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setRenaming(null)}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving || !title.trim()}>
                {saving && <Loader2Icon data-icon="inline-start" className="animate-spin" aria-hidden="true" />}
                Save
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleting !== null} onOpenChange={(open) => !open && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this conversation?</AlertDialogTitle>
            <AlertDialogDescription>
              “{deleting?.title}” and all of its messages will be permanently deleted. Items you added to your cart stay
              in the cart.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={async () => {
                if (deleting) await onDelete(deleting)
                setDeleting(null)
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </nav>
  )
}
