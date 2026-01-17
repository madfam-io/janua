'use client'

interface ToggleSettingProps {
  label: string
  description: string
  checked: boolean
  onChange: (checked: boolean) => void
}

export function ToggleSetting({ label, description, checked, onChange }: ToggleSettingProps) {
  return (
    <div className="flex items-start justify-between space-x-4 rounded-lg border p-4">
      <div className="flex-1">
        <label className="font-medium">{label}</label>
        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      </div>
      <label className="relative inline-flex cursor-pointer items-center">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="peer sr-only"
        />
        <div className="peer h-6 w-11 rounded-full bg-muted after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-border after:bg-background after:transition-all after:content-[''] peer-checked:bg-primary peer-checked:after:translate-x-full peer-checked:after:border-background"></div>
      </label>
    </div>
  )
}
