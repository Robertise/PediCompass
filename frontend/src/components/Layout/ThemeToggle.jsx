import { useThemeStore } from '../../store/themeStore'

export default function ThemeToggle() {
  const { theme, setTheme } = useThemeStore()

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light')
  }

  const getIcon = () => {
    return theme === 'light' ? 'light_mode' : 'dark_mode'
  }

  const getTooltip = () => {
    return theme === 'light' ? 'Light Mode' : 'Dark Mode'
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
