import * as React from "react"
import { Search, Command as CommandIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import { Dialog, DialogContent } from "@/components/ui/dialog"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"

interface CommandAction {
  id: string
  label: string
  description?: string
  icon?: React.ComponentType<{ className?: string }>
  keywords?: string[]
  section?: string
  onSelect: () => void
  shortcut?: string[]
}

interface CommandPaletteProps {
  actions: CommandAction[]
  open?: boolean
  onOpenChange?: (open: boolean) => void
  placeholder?: string
  emptyMessage?: string
  className?: string
}

/**
 * CommandPalette component for quick action access
 * Provides searchable command interface with keyboard shortcuts
 */
const CommandPalette = React.forwardRef<HTMLDivElement, CommandPaletteProps>(
  ({
    actions,
    open,
    onOpenChange,
    placeholder = "Type a command or search...",
    emptyMessage = "No results found.",
    className,
  }, ref) => {
    const [internalOpen, setInternalOpen] = React.useState(false)
    const isOpen = open !== undefined ? open : internalOpen
    const setIsOpen = onOpenChange || setInternalOpen

    // Group actions by section
    const groupedActions = React.useMemo(() => {
      const groups: Record<string, CommandAction[]> = {}

      actions.forEach(action => {
        const section = action.section || "Commands"
        if (!groups[section]) {
          groups[section] = []
        }
        groups[section].push(action)
      })

      return groups
    }, [actions])

    // Keyboard shortcut handler
    React.useEffect(() => {
      const down = (e: KeyboardEvent) => {
        if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
          e.preventDefault()
          setIsOpen(!isOpen)
        }
      }

      document.addEventListener("keydown", down)
      return () => document.removeEventListener("keydown", down)
    }, [isOpen, setIsOpen])

    const handleSelect = (action: CommandAction) => {
      action.onSelect()
      setIsOpen(false)
    }

    const formatShortcut = (shortcut: string[]) => {
      return shortcut.map(key => {
        switch (key.toLowerCase()) {
          case "cmd":
          case "meta":
            return "⌘"
          case "ctrl":
            return "Ctrl"
          case "shift":
            return "⇧"
          case "alt":
            return "⌥"
          default:
            return key.toUpperCase()
        }
      }).join("")
    }

    return (
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="overflow-hidden p-0" ref={ref}>
          <Command
            className={cn(
              "max-h-[400px] rounded-lg border border-border bg-background",
              className
            )}
          >
            <div className="flex items-center border-b border-border px-3">
              <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
              <CommandInput
                placeholder={placeholder}
                className="flex h-11 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
              />
              <div className="ml-2 flex items-center gap-1 text-xs text-muted-foreground">
                <CommandIcon className="h-3 w-3" />
                <span>K</span>
              </div>
            </div>

            <CommandList className="max-h-[300px] overflow-y-auto">
              <CommandEmpty className="py-6 text-center text-sm">
                {emptyMessage}
              </CommandEmpty>

              {Object.entries(groupedActions).map(([section, sectionActions]) => (
                <CommandGroup key={section} heading={section}>
                  {sectionActions.map((action) => (
                    <CommandItem
                      key={action.id}
                      value={`${action.label} ${action.description || ""} ${action.keywords?.join(" ") || ""}`}
                      onSelect={() => handleSelect(action)}
                      className="flex items-center gap-3 px-3 py-2"
                    >
                      {action.icon && (
                        <action.icon className="h-4 w-4 shrink-0" />
                      )}

                      <div className="flex-1 min-w-0">
                        <div className="font-medium">{action.label}</div>
                        {action.description && (
                          <div className="text-xs text-muted-foreground truncate">
                            {action.description}
                          </div>
                        )}
                      </div>

                      {action.shortcut && (
                        <div className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded font-mono">
                          {formatShortcut(action.shortcut)}
                        </div>
                      )}
                    </CommandItem>
                  ))}
                </CommandGroup>
              ))}
            </CommandList>
          </Command>
        </DialogContent>
      </Dialog>
    )
  }
)
CommandPalette.displayName = "CommandPalette"

/**
 * Hook for managing command palette state and actions
 */
export function useCommandPalette(actions: CommandAction[]) {
  const [open, setOpen] = React.useState(false)

  const addAction = React.useCallback((action: CommandAction) => {
    // This would integrate with a global state management system
    // For now, we just provide the interface
    console.log("Add action:", action)
  }, [])

  const removeAction = React.useCallback((actionId: string) => {
    console.log("Remove action:", actionId)
  }, [])

  return {
    open,
    setOpen,
    actions,
    addAction,
    removeAction,
  }
}

export { CommandPalette, type CommandPaletteProps, type CommandAction }