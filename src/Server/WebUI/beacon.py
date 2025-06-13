from nicegui import ui
import uuid
import time
from Modules.global_objects import beacon_list, logger, command_list
from WebUI.utils import create_header
from Modules.beacon.beacon import add_beacon_command_list

@ui.page('/beacon/{beaconUUID}')
def beacon_page(beaconUUID: str):
    ui.add_head_html('<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">')
    ui.query('body').style('font-family: "Roboto", sans-serif;')

    create_header()

    beacon = beacon_list.get(beaconUUID)

    with ui.column().classes('w-full max-w-5xl mx-auto p-4 flex-grow'):
        if not beacon:
            with ui.column().classes('w-full items-center gap-2'):
                ui.label('Beacon Not Found').classes('text-4xl font-bold mt-8 text-red-500')
                ui.label(f'No beacon with beaconUUID "{beaconUUID}" could be found. Returning to the main page.').classes('text-lg text-gray-600')
                time.sleep(2) 
            ui.navigate.to('/')
            return

        with ui.row().classes('w-full items-center justify-between no-wrap'):
            ui.button('Back', on_click=lambda: ui.navigate.to('/')).props('icon=arrow_back color=primary flat')
            ui.label('Beacon Details').classes('text-2xl font-bold text-gray-800 dark:text-gray-200')
            ui.label().classes('w-16')

        columns = [
            {'name': 'beaconUUID', 'label': 'beaconUUID', 'field': 'beaconUUID', 'align': 'left', 'sortable': True},
            {'name': 'address', 'label': 'Address', 'field': 'address', 'align': 'left', 'sortable': True},
            {'name': 'hostname', 'label': 'Hostname', 'field': 'hostname', 'sortable': True},
            {'name': 'operating_system', 'label': 'OS', 'field': 'operating_system', 'sortable': True},
            {'name': 'last_beacon', 'label': 'Last Beacon', 'field': 'last_beacon', 'sortable': True},
            {'name': 'next_beacon', 'label': 'Next Beacon', 'field': 'next_beacon', 'sortable': True},
            {'name': 'countdown', 'label': 'Expected Next Beacon', 'field': 'countdown', 'sortable': True},
        ]
        rows = [{
            'beaconUUID': beacon.uuid,
            'address': beacon.address,
            'hostname': beacon.hostname,
            'os': beacon.operating_system,
            'last_beacon': beacon.last_beacon,
            'next_beacon': beacon.next_beacon,
            'countdown': "NEed to add init"
        }]
        ui.table(columns=columns, rows=rows, row_key='beaconUUID').classes('mt-4 w-full').props('flat bordered')

        with ui.tabs().classes('w-full mt-6') as tabs:
            ui.tab('task', 'Task')
            ui.tab('results', 'Results')
            ui.tab('directory', 'Directory Listing')
            ui.tab('config', 'Config')

        with ui.tab_panels(tabs, value='task').classes('w-full mt-2 border rounded-lg p-4 dark:border-gray-700'):
            with ui.tab_panel('task'):
                ui.label('Task Information').classes('text-xl font-bold mb-4')
                task_options = {
                    'systeminfo': 'System Info', 'list_dir': 'List Directory', 'shell': 'Shell Command',
                    'close': 'Close Beacon', 'processes': 'List Processes', 'diskusage': 'Disk Usage',
                    'netstat': 'Netstat', 'session': 'Switch Session', 'takephoto': 'Take Photo'
                }
                task_select = ui.select(task_options, label='Select a Task').classes('w-full')
                arg_input = ui.input(placeholder='Enter arguments here...').classes('w-full mt-2')
                with ui.row().classes('w-full justify-end mt-4'):
                    def submit_task():
                        add_beacon_command_list(
                            beacon.uuid,
                            str(uuid.uuid4()),
                            task_select.value,
                            arg_input.value
                        )
                        
                        ui.notify(f'Task "{task_select.value}" submitted with arguments: {arg_input.value}', type='positive', position='top')
                    ui.button(
                        'Submit Task',
                        on_click=submit_task
                    )

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
                        if command.beacon_uuid != beacon.uuid:
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
                    # After refresh, the state 'completed_commands' will be updated by the logic within results_area
                    new_count = state['completed_commands']

                    if new_count > initial_count:
                        
                        ui.notify('New command result received!', position='top', type='positive')

                # Initial render
                results_area() 
                # Set the initial count
                state['completed_commands'] = len([c for c in command_list.values() if c.beacon_uuid == beacon.uuid and c.command_output is not None])
                
                ui.timer(interval=1.0, callback=check_for_updates, active=True)


            with ui.tab_panel('directory'):
                ui.label('Directory Listing').classes('text-xl font-bold mb-4')
                ui.input(placeholder='Search folders/files...').classes('w-full')
                with ui.scroll_area().classes('w-full h-64 border rounded-lg mt-2 dark:border-gray-700'):
                    ui.tree([
                        {'id': 'C:', 'label': 'C:', 'children': [
                            {'id': 'Users', 'label': 'Users', 'children': [{'id': 'Public', 'label': 'Public'}]},
                            {'id': 'Windows', 'label': 'Windows', 'children': [{'id': 'System32', 'label': 'System32'}]},
                            {'id': 'Program Files', 'label': 'Program Files'},
                        ]},
                        {'id': 'D:', 'label': 'D:'},
                    ], label_key='label', on_select=lambda e: ui.notify(f"Selected: {e.value}"))

            with ui.tab_panel('config'):
                ui.label('Beacon Configuration').classes('text-xl font-bold mb-4')
                with ui.row().classes('w-full justify-end mt-4'):
                    timer = ui.number(label='Timer', value=beacon.timer, min=0).classes('w-1/3')
                    jitter = ui.number(label='Jitter', value=beacon.jitter, min=0).classes('w-1/3')
                    def save_config():
                        add_beacon_command_list(beacon.uuid, None, "update", {
                            'timer': int(timer.value),
                            'jitter': int(jitter.value)
                        })
                        ui.notify('Configuration updated.', type='positive', position='top')
                    ui.button('Save Configuration', on_click=save_config)