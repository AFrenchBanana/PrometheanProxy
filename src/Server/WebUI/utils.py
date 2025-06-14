from nicegui import ui


dark_mode_enabled = False

def create_header():
    """Creates a reusable header with a title and dark mode switch."""
    global dark_mode_enabled

    with ui.header().classes('bg-indigo-600 dark:bg-indigo-800 shadow-lg'):
        with ui.row().classes('w-full items-center justify-between p-3'):
            with ui.row().classes('items-center'):
                ui.icon('hub', color='white', size='lg').classes('mr-2')
                ui.label('Promethean Proxy').classes('text-2xl font-bold text-white')

            def toggle_dark_mode(e):
                """Updates the global state and the UI's dark mode."""
                global dark_mode_enabled
                dark_mode_enabled = e.value
                # This will automatically update all clients
                ui.dark_mode(dark_mode_enabled)

            ui.switch('Dark Mode', value=dark_mode_enabled, on_change=toggle_dark_mode)