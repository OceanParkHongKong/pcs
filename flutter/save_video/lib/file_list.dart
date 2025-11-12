import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:html' as html;
import 'utils.dart';
import 'dart:async';

class FileListPage extends StatefulWidget {
  @override
  _FileListPageState createState() => _FileListPageState();
}

class _FileListPageState extends State<FileListPage> {
  List<Map<String, dynamic>> _files = [];
  List<Map<String, dynamic>> _filteredFiles = [];
  bool _sortAscending = true;
  int _sortColumnIndex = 0;
  int _currentPage = 1;
  final int _limit = 200;
  bool _isLoading = false;
  final TextEditingController _filterController = TextEditingController();
  Timer? _debounceTimer;
  int _totalFiles = 0;
  String _currentFilter = '';

  @override
  void initState() {
    super.initState();
    _fetchFiles();
  }

  Future<void> _fetchFiles({bool loadMore = false, String filter = ''}) async {
    if (_isLoading) return;
    setState(() {
      _isLoading = true;
    });

    final queryParams = {
      'page': '$_currentPage',
      'limit': '$_limit',
      if (filter.isNotEmpty) 'filter': filter,
    };

    final url = getServerUrl('/list_files', queryParams: queryParams);
    final response = await http.get(url).timeout(Duration(seconds: 120));

    if (response.statusCode == 200) {
      var data = jsonDecode(response.body);
      setState(() {
        if (loadMore) {
          _files.addAll(List<Map<String, dynamic>>.from(data['files']));
        } else {
          _files = List<Map<String, dynamic>>.from(data['files']);
        }
        _filteredFiles = _files;
        _totalFiles = data['total_files'];
        _isLoading = false;
      });
    } else {
      print('Failed to load files');
      setState(() {
        _isLoading = false;
      });
    }
  }

  void _onFilterChanged(String query) {
    if (_debounceTimer?.isActive ?? false) _debounceTimer!.cancel();

    _debounceTimer = Timer(Duration(seconds: 2), () {
      _currentPage = 1;
      _currentFilter = query;
      _fetchFiles(filter: query);
    });
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    super.dispose();
  }

  void _downloadFile(String filename) async {
    final url = getServerUrl('/download/$filename');
    final response = await http.get(
      url,
      headers: {'Cache-Control': 'no-cache'},
    );

    if (response.statusCode == 200) {
      final blob = html.Blob([response.bodyBytes]);
      final url = html.Url.createObjectUrlFromBlob(blob);
      final anchor = html.AnchorElement(href: url)
        ..setAttribute('download', filename)
        ..click();
      html.Url.revokeObjectUrl(url);
    } else {
      print('Failed to download file');
    }
  }

  void _sortFiles<T>(Comparable<T> Function(Map<String, dynamic>) getField, bool ascending) {
    setState(() {
      _filteredFiles.sort((a, b) {
        final aValue = getField(a);
        final bValue = getField(b);
        return ascending ? Comparable.compare(aValue, bValue) : Comparable.compare(bValue, aValue);
      });
      _sortAscending = ascending;
    });
  }

  String _formatSize(int bytes) {
    return '${(bytes / (1024 * 1024)).toStringAsFixed(2)} MB';
  }

  Widget _buildPageSelector() {
    int totalPages = (_totalFiles / _limit).ceil();
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text('Page: '),
        DropdownButton<int>(
          value: _currentPage,
          items: List.generate(totalPages, (index) => index + 1)
              .map((page) => DropdownMenuItem(
                    child: Text('$page'),
                    value: page,
                  ))
              .toList(),
          onChanged: (value) {
            setState(() {
              _currentPage = value!;
            });
            _fetchFiles(filter: _currentFilter);
          },
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('File List'),
        actions: [
          IconButton(
            icon: Icon(Icons.sort),
            onPressed: () {
              _sortFiles((file) => file['name'], _sortAscending);
            },
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: TextField(
              controller: _filterController,
              decoration: InputDecoration(
                labelText: 'Search',
                border: OutlineInputBorder(),
                suffixIcon: IconButton(
                  icon: Icon(Icons.clear),
                  onPressed: () {
                    _filterController.clear();
                    _onFilterChanged('');
                  },
                ),
              ),
              onChanged: _onFilterChanged,
            ),
          ),
          Expanded(
            child: Column(
              children: [
                Expanded(
                  child: _filteredFiles.isEmpty
                      ? Center(child: CircularProgressIndicator())
                      : SingleChildScrollView(
                          scrollDirection: Axis.vertical,
                          child: DataTable(
                            sortColumnIndex: _sortColumnIndex,
                            sortAscending: _sortAscending,
                            columns: [
                              DataColumn(
                                label: Text('Filename'),
                                onSort: (columnIndex, ascending) {
                                  _sortFiles((file) => file['name'], ascending);
                                  setState(() {
                                    _sortColumnIndex = columnIndex;
                                  });
                                },
                              ),
                              DataColumn(
                                label: Text('Created Date'),
                                onSort: (columnIndex, ascending) {
                                  _sortFiles((file) => file['created'], ascending);
                                  setState(() {
                                    _sortColumnIndex = columnIndex;
                                  });
                                },
                              ),
                              DataColumn(
                                label: Text('Size (MB)'),
                                onSort: (columnIndex, ascending) {
                                  _sortFiles((file) => file['size'], ascending);
                                  setState(() {
                                    _sortColumnIndex = columnIndex;
                                  });
                                },
                              ),
                              DataColumn(label: Text('Actions')),
                            ],
                            rows: _filteredFiles.map((file) {
                              return DataRow(
                                cells: [
                                  DataCell(Text(file['name'])),
                                  DataCell(Text(file['created'])),
                                  DataCell(Text(_formatSize(file['size']))),
                                  DataCell(
                                    IconButton(
                                      icon: Icon(Icons.download),
                                      onPressed: () => _downloadFile(file['name']),
                                    ),
                                  ),
                                ],
                              );
                            }).toList(),
                          ),
                        ),
                ),
                if (_isLoading)
                  Padding(
                    padding: const EdgeInsets.all(8.0),
                    child: CircularProgressIndicator(),
                  ),
                if (!_isLoading) _buildPageSelector(),
              ],
            ),
          ),
        ],
      ),
    );
  }
}