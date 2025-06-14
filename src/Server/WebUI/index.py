from nicegui import ui
import time
import traceback
from Modules.global_objects import beacon_list, logger, sessions_list
from WebUI.utils import create_header, dark_mode_enabled


def start_webui_server():
    """
    Starts the NiceGUI web server for the Promethean Proxy WebUI.
    """
    logger.info("Starting Promethean Proxy WebUI server...")
    ui.run(title='Promethean Proxy',
           port=9000,
           reload=False,
           show=False)

@ui.page('/')
def index_page():
    """
    A modern, colorful, and responsive index page for the Promethean Proxy UI.
    """
    # Set the page's dark mode state from the global variable
    ui.dark_mode(dark_mode_enabled)

    # A dictionary to hold state that persists across UI updates on this page.
    state = {'known_beacon_count': len(beacon_list)}

    create_header()

    # Main content area
    with ui.column().classes('dark:bg-slate-900 w-full max-w-6xl mx-auto p-4 flex-grow flex flex-col items-center'):
        
        # --- Live Beacons Section ---
        ui.label('Live Beacons').classes('text-4xl font-bold mt-8 mb-4 text-indigo-600 dark:text-indigo-400 text-center')
        with ui.card().classes('w-full p-0 shadow-xl rounded-lg flex-grow flex flex-col'):
            beacon_spinner_row = ui.row().classes('w-full justify-center p-8 flex-grow items-center')
            with beacon_spinner_row:
                ui.spinner(size='lg', color='indigo')
                ui.label('Waiting for beacons...').classes('ml-4 text-lg text-gray-500')

            beacon_columns = [
                {'name': 'uuid', 'label': 'UUID', 'field': 'uuid', 'align': 'left', 'sortable': True},
                {'name': 'address', 'label': 'Address', 'field': 'address', 'align': 'left', 'sortable': True},
                {'name': 'hostname', 'label': 'Hostname', 'field': 'hostname', 'sortable': True},
                {'name': 'operating_system', 'label': 'OS', 'field': 'operating_system', 'sortable': True},
                {'name': 'last_beacon', 'label': 'Last Beacon', 'field': 'last_beacon', 'sortable': True},
                {'name': 'next_beacon', 'label': 'Next Beacon', 'field': 'next_beacon', 'sortable': True},
                {'name': 'countdown', 'label': 'Countdown', 'field': 'countdown', 'sortable': True},
            ]

            with ui.element('div').classes('overflow-x-auto w-full flex-grow'):
                beacon_table = ui.table(columns=beacon_columns, rows=[], row_key='uuid').classes('min-w-full')
                beacon_table.props('header-class="bg-indigo-200 dark:bg-indigo-950 text-gray-800 dark:text-white"')
                ui.add_head_html('''
                    <style>
                        .q-table tbody tr:hover {
                            background-color: rgba(99, 102, 241, 0.1) !important;
                        }
                    </style>
                ''')
                beacon_table.on('row-click', lambda e: ui.navigate.to(f"/beacon/{e.args[1]['uuid']}"))

            def update_beacons_table():
                """Updates the BEACONS table and shows a notification for new beacons."""
                current_beacon_count = len(beacon_list)
                
                beacon_spinner_row.visible = (current_beacon_count == 0)
                beacon_table.visible = (current_beacon_count > 0)

                if current_beacon_count > state['known_beacon_count']:
                    ui.notification('New beacon connection!', position='top', type='positive', timeout=3000)
                
                state['known_beacon_count'] = current_beacon_count

                rows = []
                now = time.time()
                for b_id, beacon in beacon_list.items():
                    try:
                        last_ts = time.mktime(time.strptime(beacon.last_beacon, '%a %b %d %H:%M:%S %Y'))
                        next_ts = last_ts + beacon.timer
                        delta = int(next_ts - now)
                        next_display = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_ts))
                        
                        if delta > 0:
                            countdown_str = f"{delta}s"
                        elif delta > -beacon.jitter:
                            countdown_str = f"Late by {-delta}s (Jitter: {beacon.jitter}s)"
                        else:
                            countdown_str = f'Missed by {abs(delta)}s'
                    except (ValueError, TypeError):
                        next_display = str(beacon.next_beacon)
                        countdown_str = 'N/A'
                    
                    rows.append({
                        'uuid': b_id, 'address': beacon.address[0] + beacon.address[1], 'hostname': beacon.hostname,
                        'operating_system': beacon.operating_system, 'last_beacon': str(beacon.last_beacon),
                        'next_beacon': next_display, 'countdown': countdown_str,
                    })
                
                beacon_table.rows = rows

            ui.timer(1.0, update_beacons_table, active=True)

        # --- Live Sessions Section ---
        ui.label('Live Sessions').classes('text-4xl font-bold mt-8 mb-4 text-indigo-600 dark:text-indigo-400 text-center')
        with ui.card().classes('w-full p-0 shadow-xl rounded-lg flex-grow flex flex-col'):
            sessions_spinner_row = ui.row().classes('w-full justify-center p-8 flex-grow items-center')
            with sessions_spinner_row:
                ui.spinner(size='lg', color='indigo')
                ui.label('Waiting for Sessions...').classes('ml-4 text-lg text-gray-500')

            sessions_columns = [
                {'name': 'uuid', 'label': 'UUID', 'field': 'uuid', 'align': 'left', 'sortable': True},
                {'name': 'address', 'label': 'Address', 'field': 'address', 'align': 'left', 'sortable': True},
                {'name': 'hostname', 'label': 'Hostname', 'field': 'hostname', 'sortable': True},
                {'name': 'operating_system', 'label': 'OS', 'field': 'operating_system', 'sortable': True},
            ]

            with ui.element('div').classes('overflow-x-a-auto w-full flex-grow'):
                sessions_table = ui.table(columns=sessions_columns, rows=[], row_key='uuid').classes('min-w-full')
                sessions_table.props('header-class="bg-indigo-200 dark:bg-indigo-950 text-gray-800 dark:text-white"')
                sessions_table.on('row-click', lambda e: ui.navigate.to(f"/session/{e.args[1]['uuid']}"))

            def update_sessions_table():
                """Updates the SESSIONS table."""
                current_session_count = len(sessions_list)
                sessions_spinner_row.visible = (current_session_count == 0)
                sessions_table.visible = (current_session_count > 0)

                rows = []
                for s_id, session in sessions_list.items():
                    rows.append({
                        'uuid': s_id,
                        'address': session.address[0] + ":" + str(session.address[1]),
                        'hostname': session.hostname,
                        'operating_system': session.operating_system,
                    })
                sessions_table.rows = rows
                
            ui.timer(1.0, update_sessions_table, active=True)