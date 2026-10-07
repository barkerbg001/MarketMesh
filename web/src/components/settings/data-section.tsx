import { useState } from 'react'
import { DownloadIcon, Trash2Icon } from 'lucide-react'
import { toast } from 'sonner'

import { ClearCartButton } from '@/components/cart/cart-sheet'
import { SettingsSection } from '@/components/settings/settings-section'
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { useCart } from '@/hooks/use-cart'
import { CONVERSATIONS_CHANGED_EVENT, deleteJson, downloadExport, errorMessage } from '@/lib/api'

const CONFIRM_WORD = 'DELETE'

function DeleteHistoryButton() {
  const [confirm, setConfirm] = useState('')
  const [open, setOpen] = useState(false)

  const deleteAll = async () => {
    try {
      const result = await deleteJson<{ deleted: number }>('/api/conversations', 'Could not delete history', {
        confirm: CONFIRM_WORD,
      })
      toast.success(result.deleted ? 'Conversation history deleted' : 'There was no history to delete')
      setOpen(false)
      window.dispatchEvent(new Event(CONVERSATIONS_CHANGED_EVENT))
    } catch (err) {
      toast.error(errorMessage(err, 'Could not delete history'))
    }
  }

  return (
    <AlertDialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (!next) setConfirm('')
      }}
    >
      <AlertDialogTrigger asChild>
        <Button variant="destructive">
          <Trash2Icon data-icon="inline-start" aria-hidden="true" />
          Delete all conversations
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete all conversation history?</AlertDialogTitle>
          <AlertDialogDescription>
            Every conversation, message, product card and comparison will be permanently deleted. Your cart and settings
            are kept. Consider exporting first.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="confirm-delete-history">Type {CONFIRM_WORD} to confirm</Label>
          <Input
            id="confirm-delete-history"
            value={confirm}
            autoComplete="off"
            onChange={(event) => setConfirm(event.target.value)}
          />
        </div>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <Button variant="destructive" disabled={confirm !== CONFIRM_WORD} onClick={() => void deleteAll()}>
            Delete everything
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

export function DataSection() {
  const { cart, clearCart } = useCart()

  return (
    <SettingsSection
      title="Your data"
      description="Everything is stored by the API in its local SQLite database. Nothing is shared with other users."
    >
      <div className="flex flex-col gap-2">
        <h3 className="text-sm font-medium">Conversations</h3>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => downloadExport('/api/conversations/export?format=markdown')}>
            <DownloadIcon data-icon="inline-start" aria-hidden="true" />
            Export all as Markdown
          </Button>
          <Button variant="outline" onClick={() => downloadExport('/api/conversations/export?format=json')}>
            <DownloadIcon data-icon="inline-start" aria-hidden="true" />
            Export all as JSON
          </Button>
          <DeleteHistoryButton />
        </div>
      </div>

      <Separator />

      <div className="flex flex-col gap-2">
        <h3 className="text-sm font-medium">Cart ({cart.item_count} items)</h3>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" disabled={!cart.items.length} onClick={() => downloadExport('/api/cart/export?format=csv')}>
            <DownloadIcon data-icon="inline-start" aria-hidden="true" />
            Export as CSV
          </Button>
          <Button variant="outline" disabled={!cart.items.length} onClick={() => downloadExport('/api/cart/export?format=json')}>
            <DownloadIcon data-icon="inline-start" aria-hidden="true" />
            Export as JSON
          </Button>
          <ClearCartButton onConfirm={() => void clearCart()} disabled={!cart.items.length} />
        </div>
      </div>
    </SettingsSection>
  )
}
