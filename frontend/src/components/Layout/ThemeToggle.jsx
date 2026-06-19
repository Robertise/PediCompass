import { useThemeStore } from '../../store/themeStore'

export default function ThemeToggle() {
  const { theme, setTheme } = useThemeStore()

  const toggleTheme = () => {
    if (theme === 'light') setTheme('dark')
    else if (theme === 'dark') setTheme('system')
    else setTheme('light')
  }

  const getIcon = () => {
    if (theme === 'light') return 'light_mode'
    if (theme === 'dark') return 'dark_mode'
    return 'brightness_auto'
  }

  const getTooltip = () => {
    if (theme === 'light') return 'Light Mode'
    if (theme === 'dark') return 'Dark Mode'
    return 'System Theme'
  }

  return (
    <button
      onClick={toggleTheme}
      title={getTooltip()}
      className="w-10 h-10 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-variant/50 transition-colors"
    >
      <span className="material-symbols-outlined text-[20px]">{getIcon()}</span>
    </button>
  )
}
