import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import 'file_list.dart';
import 'utils.dart';

void main() {
  runApp(ScriptManagerApp());
}

class ScriptManagerApp extends StatefulWidget {
  @override
  _ScriptManagerAppState createState() => _ScriptManagerAppState();
}

class _ScriptManagerAppState extends State<ScriptManagerApp> {
  bool _isDarkTheme = true;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      theme: _isDarkTheme ? ThemeData.dark() : ThemeData.light(),
      home: ScriptManagerPage(toggleTheme: _toggleTheme),
      routes: {
        '/files': (context) => FileListPage(),
      },
    );
  }

  void _toggleTheme() {
    setState(() {
      _isDarkTheme = !_isDarkTheme;
    });
  }
}

class ScriptManagerPage extends StatefulWidget {
  final VoidCallback toggleTheme;

  ScriptManagerPage({required this.toggleTheme});

  @override
  _ScriptManagerPageState createState() => _ScriptManagerPageState();
}

class _ScriptManagerPageState extends State<ScriptManagerPage> {
  List<bool> _selected = [];
  List<Map<String, String>> _data = [];
  String _logText = '';
  Timer? _timer;
  int _sortColumnIndex = 0;
  bool _sortAscending = true;

  @override
  void initState() {
    super.initState();
    _fetchCameraNames();
    _startStatusUpdates();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _fetchCameraNames() async {
    final url = getServerUrl('/camera_names');
    final response = await http.get(url);
    if (response.statusCode == 200) {
      List<dynamic> cameraNames = jsonDecode(response.body);
      setState(() {
        _data = cameraNames.map((name) => <String, String>{'name': name.toString(), 'status': 'Unknown', 'duration': 'Unknown'}).toList();
        _selected = List<bool>.generate(_data.length, (_) => false);
      });
    } else {
      print('Failed to load camera names');
    }
  }

  void _startStatusUpdates() {
    _timer = Timer.periodic(const Duration(seconds: 10), (timer) {
      _updateCameraStatuses();
    });
  }

  Future<void> _updateCameraStatuses() async {
    for (var i = 0; i < _data.length; i++) {
      String cameraName = _data[i]['name']!;
      final response = await http.get(getServerUrl('/status/$cameraName'));
      if (response.statusCode == 200) {
        var data = jsonDecode(response.body);
        
        String durationText = 'Unknown';
        if (data['status'] == 'running') {
          final durationResponse = await http.get(getServerUrl('/duration/$cameraName'));
          if (durationResponse.statusCode == 200) {
            var durationData = jsonDecode(durationResponse.body);
            durationText = _formatDuration(durationData['duration']);
          }
        }

        setState(() {
          _data[i]['status'] = data['status'];
          _data[i]['duration'] = durationText;
        });
      }
    }
  }

  String _formatDuration(double duration) {
    final int seconds = duration.toInt();
    final int hours = seconds ~/ 3600;
    final int minutes = (seconds % 3600) ~/ 60;
    final int secs = seconds % 60;
    return '${hours.toString().padLeft(2, '0')}:${minutes.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}';
  }

  Future<void> _toggleCameraStatus(String cameraName, String currentStatus) async {
    final action = currentStatus == 'running' ? 'stop' : 'start';
    final response = await http.post(getServerUrl('/$action/$cameraName'));
    if (response.statusCode == 200) {
      _updateCameraStatuses();
    } else {
      print('Failed to $action camera $cameraName');
    }
  }

  Future<void> _fetchLog(String cameraName) async {
    final response = await http.get(getServerUrl('/status/$cameraName'));
    if (response.statusCode == 200) {
      var data = jsonDecode(response.body);
      setState(() {
        _logText = data['log'] ?? 'no log'; 
      });
    }
  }

  void _toggleSelectedCameras() {
    for (var i = 0; i < _data.length; i++) {
      if (_selected[i]) {
        _toggleCameraStatus(_data[i]['name']!, _data[i]['status']!);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Camera Record Script Manager'),
        actions: [
          IconButton(
            icon: Icon(Icons.brightness_6),
            onPressed: widget.toggleTheme,
          ),
          IconButton(
            icon: Icon(Icons.attach_file),
            onPressed: () => Navigator.pushNamed(context, '/files'),
          ),
          IconButton(
            icon: Icon(Icons.notifications),
            onPressed: () {},
          ),
          IconButton(
            icon: Icon(Icons.settings),
            onPressed: () {},
          ),
          CircleAvatar(
            backgroundImage: NetworkImage('https://via.placeholder.com/150'),
          ),
        ],
      ),
      body: Row(
        children: [
          Expanded(
            flex: 3,
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Script Status',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: _toggleSelectedCameras,
                    child: Text('Batch Start/Stop Cameras'),
                  ),
                  SizedBox(height: 16),
                  Expanded(
                    child: Center(
                      child: SingleChildScrollView(
                        scrollDirection: Axis.vertical,
                        child: SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: DataTable(
                            sortColumnIndex: _sortColumnIndex,
                            sortAscending: _sortAscending,
                            showCheckboxColumn: true,
                            columns: [
                              DataColumn(
                                label: Text('Script Name'),
                                onSort: (columnIndex, ascending) => _sort((d) => d['name']!, columnIndex, ascending),
                              ),
                              DataColumn(
                                label: Text('Last Status'),
                                onSort: (columnIndex, ascending) => _sort((d) => d['status']!, columnIndex, ascending),
                              ),
                              DataColumn(
                                label: Text('Duration'),
                                onSort: (columnIndex, ascending) => _sort((d) => d['duration']!, columnIndex, ascending),
                              ),
                              DataColumn(label: Text('Actions')),
                            ],
                            rows: List<DataRow>.generate(
                              _data.length,
                              (index) => DataRow(
                                selected: _selected[index],
                                onSelectChanged: (bool? value) {
                                  setState(() {
                                    _selected[index] = value!;
                                    if (value) {
                                      _fetchLog(_data[index]['name']!);
                                    } else {
                                      _logText = '';
                                    }
                                  });
                                },
                                cells: [
                                  DataCell(Text(_data[index]['name']!)),
                                  DataCell(Text(_data[index]['status']!)),
                                  DataCell(Text(_data[index]['duration']!)),
                                  DataCell(
                                    ElevatedButton(
                                      onPressed: () => _toggleCameraStatus(_data[index]['name']!, _data[index]['status']!),
                                      child: Text(_data[index]['status'] == 'running' ? 'Stop' : 'Start'),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          VerticalDivider(),
          Expanded(
            flex: 2,
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Recent Activity',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  SizedBox(height: 16),
                  if (_logText.isNotEmpty)
                    _buildActivityCard('Log Details', _logText, DateTime.now().toString()),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActivityCard(String title, String description, String date) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8.0),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: TextStyle(fontWeight: FontWeight.bold)),
            SizedBox(height: 8),
            Text(description),
            SizedBox(height: 8),
            Text(date, style: TextStyle(color: Colors.grey)),
          ],
        ),
      ),
    );
  }

  void _sort<T>(Comparable<T> Function(Map<String, String>) getField, int columnIndex, bool ascending) {
    setState(() {
      _sortColumnIndex = columnIndex;
      _sortAscending = ascending;
      _data.sort((a, b) {
        final aValue = getField(a);
        final bValue = getField(b);
        return ascending ? Comparable.compare(aValue, bValue) : Comparable.compare(bValue, aValue);
      });
    });
  }
}