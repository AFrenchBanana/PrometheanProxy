from nicegui import ui
import time
from Modules.global_objects import sessions_list, logger, command_list
from WebUI.utils import create_header, dark_mode_enabled
from Modules.beacon.beacon import add_beacon_command_list
import json
import os

@ui.page('/session/{sessionUUID}')
def session_page(sessionUUID: str):
    ui.dark_mode(dark_mode_enabled)

    ui.add_head_html('<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">')
    ui.query('body').style('font-family: "Roboto", sans-serif;')

    create_header()

    session = sessions_list.get(sessionUUID)

    with ui.column().classes('w-full max-w-5xl mx-auto p-4 flex-grow'):
        if not session:
            with ui.column().classes('w-full items-center gap-2'):
                ui.label('Beacon Not Found').classes('text-4xl font-bold mt-8 text-red-500')
                ui.label(f'No beacon with beaconUUID "{sessionUUID}" could be found. Returning to the main page.').classes('text-lg text-gray-600')
                time.sleep(2) 
            ui.navigate.to('/')
            return

        with ui.row().classes('w-full items-center justify-between no-wrap'):
            ui.button('Back', on_click=lambda: ui.navigate.to('/')).props('icon=arrow_back color=primary flat')
            ui.label('Session Details').classes('text-2xl font-bold text-gray-800 dark:text-gray-200')
            ui.label().classes('w-16')

        columns = [
                {'name': 'uuid', 'label': 'UUID', 'field': 'uuid', 'align': 'left', 'sortable': True},
                {'name': 'address', 'label': 'Address', 'field': 'address', 'align': 'left', 'sortable': True},
                {'name': 'hostname', 'label': 'Hostname', 'field': 'hostname', 'sortable': True},
                {'name': 'operating_system', 'label': 'OS', 'field': 'operating_system', 'sortable': True},
            ]
        rows = [{
            'sessionUUID': session.uuid,
            'address': session.address,
            'hostname': session.hostname,
            'os': session.operating_system,
            'last_beacon': session.last_beacon,
            'next_beacon': session.next_beacon,
        }]
        ui.table(columns=columns, rows=rows, row_key='sessionUUID').classes('mt-4 w-full').props('flat bordered')

        with ui.tabs().classes('w-full mt-6') as tabs:
            ui.tab('task', 'Task')
            ui.tab('results', 'Results')
            ui.tab('directory', 'Directory Listing')
            ui.tab('config', 'Config')

        with ui.tab_panels(tabs, value='task').classes('w-full mt-2 border rounded-lg p-4 dark:border-gray-700'):
            with ui.tab_panel('task'):
                ui.label('Task Information').classes('text-xl font-bold mb-4')
                # Combined commands definition: label and argument schemas
                commands = {
                    'system_info': {'label': 'System Info', 'args': []},
                    'list_dir': {'label': 'List Directory', 'args': [{'name': 'path', 'type': 'text'}]},
                    'shell': {'label': 'Shell Command', 'args': [{'name': 'command', 'type': 'text'}]},
                    'processes': {'label': 'List Processes', 'args': []},
                    'diskusage': {'label': 'Disk Usage', 'args': []},
                    'netstat': {'label': 'Netstat', 'args': []},
                    'session': {'label': 'Switch Session', 'args': [{'name': 'session_id', 'type': 'number'}]},
                    'directory_traversal': {'label': 'Directory Traversal', 'args': [{'name': 'path', 'type': 'text'}]},
                    'close': {'label': 'Close Beacon', 'args': []},
                }
                # Build select options from combined commands
                select_options = {key: cfg['label'] for key, cfg in commands.items()}
                # Initialize select with default value to render args initially
                task_select = ui.select(select_options, label='Select a Task', value=list(commands.keys())[0]).classes('w-full')
                # Container to render dynamic argument inputs
                args_container = ui.column().classes('w-full mt-2')
                # Store input widgets to retrieve values later
                arg_widgets = {}

                def render_args():
                    # Clear previous inputs
                    args_container.clear()
                    arg_widgets.clear()
                    schema = commands.get(task_select.value, {}).get('args', [])
                    for arg_def in schema:
                        name = arg_def['name']
                        typ = arg_def.get('type', 'text')
                        # Render appropriate input widget based on type
                        # Render input within the args container context
                        with args_container:
                            if typ == 'number':
                                widget = ui.number(label=name.replace('_', ' ').title(), placeholder=f'Enter {name}').classes('w-full')
                            else:
                                widget = ui.input(label=name.replace('_', ' ').title(), placeholder=f'Enter {name}').classes('w-full')
                        # Store for later
                        arg_widgets[name] = widget

                # Update args on command change (watch select value)
                task_select.on('update:model-value', lambda e: render_args())
                # Initial render
                render_args()

                with ui.row().classes('w-full justify-end mt-4'):
                    def submit_task():
                        # Collect argument values
                        data = {}
                        for name, widget in arg_widgets.items():
                            data[name] = widget.value
                        payload = data if data else None
                        add_beacon_command_list(
                            
                        )
                        ui.notify(f'Task "{task_select.value}" submitted.', type='positive', position='top')
                    # Submit button
                    ui.button('Submit Task', on_click=submit_task).classes('primary')

            with ui.tab_panel('results'):
                # Use a mutable object (like a list) to store the count so it can be modified in the callback
                state = {'completed_commands': 0}

                @ui.refreshable
                def results_area():
                    ui.label('Command Results').classes('text-xl font-bold mb-4')
                    result_cols = [
                        {'name': 'id', 'label': 'Command ID', 'field': 'id', 'align': 'left'},
                        {'name': 'cmd', 'label': 'Command', 'field': 'cmd', 'align': 'left'},
                        {'name': 'data', 'label': 'Data', 'field': 'data', 'align': 'left'},
                        {'name': 'resp', 'label': 'Response', 'field': 'resp', 'align': 'left', 'style': 'white-space: pre-wrap;'},
                    ]
                    
                    result_rows = []
                    completed_now = 0
                    for command in sorted(command_list.values(), key=lambda c: getattr(c, 'timestamp', 0)):
                        if command.session_uuid != sessionUUID.uuid:
                            continue
                        
                        if command.command_output is not None:
                            completed_now += 1

                        result_rows.append({
                            'id': command.command_uuid,
                            'cmd': command.command,
                            'data': command.command_data,
                            'resp': command.command_output if command.command_output is not None else '⏳ Pending...',
                        })
                    
                    # Update the state count after building the rows
                    state['completed_commands'] = completed_now

                    results_table = ui.table(columns=result_cols, rows=result_rows, row_key='id').classes('w-full')
                    
                    if not result_rows:
                        with results_table.add_slot('no-data'):
                            with ui.row().classes('w-full items-center justify-center gap-2 m-4'):
                                ui.icon('info', size='lg', color='gray-500')
                                ui.label('No command history available.').classes('text-gray-500')
                
                # This function will be the timer's callback
                def check_for_updates():
                    initial_count = state['completed_commands']
                    results_area.refresh()
                    new_count = state['completed_commands']

                    if new_count > initial_count:
                        
                        ui.notify('New command result received!', position='top', type='positive')

                results_area() 
                # Set the initial count
                state['completed_commands'] = len([c for c in command_list.values() if c.beacon_uuid == beacon.uuid and c.command_output is not None])
                
                ui.timer(interval=1.0, callback=check_for_updates, active=True)


            with ui.tab_panel('directory'):
                ui.label('Directory Viewer').classes('text-xl font-bold mb-4')
                search_input = ui.input(placeholder='Search files/directories...').classes('w-full mb-2')

                tree_col = ui.column().classes('w-full')

                ICON_MAP = {
                    '.pdf': 'picture_as_pdf',
                    '.doc': 'description', '.docx': 'description',
                    '.ppt': 'slideshow', '.pptx': 'slideshow',
                    '.xls': 'grid_on', '.xlsx': 'grid_on', '.csv': 'table_chart',
                    '.txt': 'article', '.md': 'article', '.log': 'receipt_long',
                    '.jpg': 'image', '.jpeg': 'image', '.png': 'image', '.gif': 'image', '.bmp': 'image', '.svg': 'image',
                    '.py': 'code', '.js': 'javascript', '.html': 'html', '.css': 'css', '.sh': 'terminal',
                    '.go': 'code_blocks', '.mod': 'list_alt', '.sum': 'summarize', '.json': 'data_object',
                    '.zip': 'archive', '.gz': 'archive', '.tar': 'archive', '.rar': 'archive',
                    '.mp3': 'music_note', '.wav': 'music_note', '.ogg': 'music_note',
                    '.mp4': 'movie', '.avi': 'movie', '.mov': 'movie', '.mkv': 'movie',
                    '.db': 'database',
                }
                DEFAULT_FILE_ICON = 'insert_drive_file'
                
                tree_ref = {}  # Holds a reference to the current ui.tree instance
                id_meta_map = {}  # Maps node ID to its metadata for quick lookup
                expanded_node_ids = []

                # --- Core Functions ---
                def filter_data(data_dict, term):
                    """Recursively filter directory data by search term."""
                    result = {}
                    term = term.lower()
                    for name, content in data_dict.items():
                        lower_name = name.lower()
                        if term in lower_name:
                            result[name] = content
                        elif isinstance(content, dict) and 'size' not in content:
                            filtered = filter_data(content, term)
                            if filtered:
                                result[name] = filtered
                    return result

                def show_file_details_dialog(node_id: str):
                    """Creates and opens a dialog with details for the selected file."""
                    meta = id_meta_map.get(node_id)
                    if not meta: return

                    with ui.dialog() as dialog, ui.card().classes('w-full max-w-md'):
                        ui.label(f'Details for {os.path.basename(node_id)}').classes('text-lg font-bold')
                        ui.separator()
                        ui.markdown(f"""
                            - **Size:** `{meta.get('size', 'N/A')} bytes`
                            - **Last Modified:** `{meta.get('lastModified', 'N/A')}`
                            - **Attributes:** `{meta.get('attributes', 'N/A')}`
                        """).classes('mt-2 mb-4')
                        with ui.row().classes('w-full justify-end'):
                            ui.button('Close', on_click=dialog.close).props('flat color=primary')
                    dialog.open()

                def handle_selection(e):
                    """Handles clicks on any item in the tree."""
                    if not e.value: return
                    
                    node_id = e.value
                    tree = tree_ref.get('instance')
                    if not tree: return

                    if node_id in id_meta_map:
                        show_file_details_dialog(node_id)
                    else:
                        if node_id in expanded_node_ids:
                            tree.collapse([node_id]) 
                            expanded_node_ids.remove(node_id)
                        else:
                            tree.expand([node_id]) 
                            expanded_node_ids.append(node_id)

                    if tree_ref.get('instance'):
                        tree_ref['instance'].value = None

                def load_directory():
                    """Loads directory data, builds, and renders the tree."""
                    tree_col.clear()
                    id_meta_map.clear() # Clear metadata map, but keep the expanded state

                    file_path = os.path.expanduser(f"~/.PrometheanProxy/{beacon.uuid}/directory_traversal.json")
                    if not os.path.exists(file_path):
                        with tree_col:
                            ui.label('Waiting for directory traversal data...').classes('text-gray-500')
                        return False

                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                    except Exception as e:
                        with tree_col:
                            ui.label(f"Error parsing JSON: {e}").classes('text-red-500')
                        return True
                    # Apply search filter
                    term = (search_input.value or '').lower().strip()
                    data_to_build = filter_data(data, term) if term else data

                    def build_nodes_recursive(data_dict, parent_path=''):
                        node_list = []
                        for name, content in data_dict.items():
                            current_path = os.path.join(parent_path, name)
                            is_file = 'size' in content
                            if is_file:
                                _, extension = os.path.splitext(name)
                                icon = ICON_MAP.get(extension.lower(), DEFAULT_FILE_ICON)
                                node = {'id': current_path, 'label': name, 'icon': icon}
                                id_meta_map[current_path] = content
                                node_list.append(node)
                            else:
                                node = {'id': current_path, 'label': name, 'icon': 'folder_open', 'children': build_nodes_recursive(content, current_path)}
                                node_list.append(node)
                        return sorted(node_list, key=lambda x: (x['icon'] == 'folder_open', x['label'].lower()), reverse=True)

                    nodes = build_nodes_recursive(data_to_build)
                    
                    with tree_col:
                        if not nodes:
                            ui.label('No files or directories found.').classes('text-gray-500')
                        else:
                            # CORRECTED: Pass our state list to the 'expanded' parameter on creation.
                            tree = ui.tree(nodes, label_key='label', on_select=handle_selection)
                            tree_ref['instance'] = tree
                            # Restore expansion state after creation
                            if expanded_node_ids:
                                tree.expand(expanded_node_ids)
                    return True

                # --- Initial Load & Search Refresh ---
                # Refresh listing when search term changes
                search_input.on('update:model-value', lambda e: load_directory())
                # Initial load
                load_directory()
                # Auto-refresh every second until directory JSON is available
                ui.timer(1.0, load_directory)
                # Manual refresh button
                ui.button('Refresh', on_click=load_directory).classes('primary mt-2')