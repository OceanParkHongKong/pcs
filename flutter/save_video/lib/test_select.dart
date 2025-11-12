import 'package:flutter/material.dart';

class TestSelectPage extends StatefulWidget {
  @override
  _TestSelectPageState createState() => _TestSelectPageState();
}

class _TestSelectPageState extends State<TestSelectPage> {
  List<bool> _selected = List<bool>.generate(5, (index) => false);

  List<Map<String, String>> _data = [
    {'name': 'Camera 1', 'status': 'Running', 'duration': '02:30:00'},
    {'name': 'Camera 2', 'status': 'Stopped', 'duration': '00:00:00'},
    {'name': 'Camera 3', 'status': 'Running', 'duration': '01:15:30'},
    {'name': 'Camera 4', 'status': 'Stopped', 'duration': '00:00:00'},
    {'name': 'Camera 5', 'status': 'Running', 'duration': '00:45:15'},
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Test Select Page'),
      ),
      body: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          showCheckboxColumn: true,
          columns: [
            DataColumn(label: Text('Camera Name')),
            DataColumn(label: Text('Status')),
            DataColumn(label: Text('Duration')),
          ],
          rows: List<DataRow>.generate(
            _data.length,
            (index) => DataRow(
              selected: _selected[index],
              onSelectChanged: (bool? value) {
                setState(() {
                  _selected[index] = value!;
                });
              },
              cells: [
                DataCell(Text(_data[index]['name']!)),
                DataCell(Text(_data[index]['status']!)),
                DataCell(Text(_data[index]['duration']!)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}