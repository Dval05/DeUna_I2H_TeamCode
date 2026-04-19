import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../models/user_model.dart';

class AmbiguousQuestionWarning {
  const AmbiguousQuestionWarning({
    required this.title,
    required this.message,
    this.relatedQuestion,
  });

  final String title;
  final String message;
  final String? relatedQuestion;

  factory AmbiguousQuestionWarning.fromJson(Map<String, dynamic> json) {
    return AmbiguousQuestionWarning(
      title: json['title'] as String? ?? 'Pregunta ambigua',
      message: json['message'] as String? ??
          'Tu pregunta puede tener varias interpretaciones.',
      relatedQuestion: json['relatedQuestion'] as String?,
    );
  }
}

class ApiService {
  // Configura la URL base del backend Flask.
  // Para emulador Android: 'http://10.0.2.2:5000'
  // Para iOS Simulator: 'http://localhost:5000'
  // Para dispositivo físico en la misma red: la IP de tu PC en la red local (ej. 'http://192.168.1.100:5000')
  // ¡Importante! Asegúrate de que tu PC y el dispositivo/emulador estén en la misma red si usas IP local.
  // Para el reto, puedes usar 'http://localhost:5000' y configurar el emulador si es necesario,
  // o usar la IP local de tu máquina si pruebas en un dispositivo físico.
  String get _baseUrl {
    if (!kDebugMode) {
      return 'http://tu_ip_produccion:8000';
    }

    if (kIsWeb) {
      return 'http://localhost:8000';
    }

    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return 'http://10.0.2.2:8000';
      case TargetPlatform.iOS:
      case TargetPlatform.macOS:
      case TargetPlatform.windows:
      case TargetPlatform.linux:
      case TargetPlatform.fuchsia:
        return 'http://localhost:8000';
    }
  }

  static const List<String> _fallbackQuickReplies = [
    '¿Cuánto vendí en total el día de hoy?',
    'De lo que vendí esta semana, ¿cuál fue mi ganancia real?',
    '¿Qué es lo que más me compran mis clientes?',
    '¿Cuántos clientes frecuentes tengo registrados?',
    '¿A qué hora se llena más mi local normalmente?',
    '¿Cuánto dinero me entró por transferencias vs QR Deuna este mes?',
    '¿Cuánto vendí el domingo pasado?',
    '¿Gané más dinero este mes o el mes pasado?',
    '¿Cuánto gasta la gente en promedio cada vez que me compra?',
    '¿He conseguido clientes nuevos esta semana?',
  ];

  static const Map<String, Map<String, String>> _debugAmbiguousRules = {
    'ganancia': {
      'title': 'Pregunta ambigua detectada',
      'message':
          '“Ganancia” puede significar utilidad neta, margen o ingresos brutos. Aclárala antes de consultar.',
      'relatedQuestion': '¿Cuál fue mi ganancia real?'
    },
    'vendi': {
      'title': 'Pregunta ambigua detectada',
      'message':
          'La API futura puede pedir un rango de tiempo cuando preguntas cuánto vendiste.',
      'relatedQuestion': '¿Cuánto vendí en total el día de hoy?'
    },
    'clientes frecuentes': {
      'title': 'Pregunta ambigua detectada',
      'message':
          '“Cliente frecuente” depende del criterio definido por la API y puede requerir un período o umbral.',
      'relatedQuestion': '¿Cuántos clientes frecuentes tengo registrados?'
    },
  };

  Future<List<String>> fetchSuggestedQuestions() async {
    if (kDebugMode) {
      return List<String>.from(_fallbackQuickReplies);
    }

    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/chat/suggested-questions'),
        headers: {'Content-Type': 'application/json; charset=UTF-8'},
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final rawQuestions = data['questions'];
        final questions = rawQuestions is List
            ? rawQuestions
                .map((question) => question?.toString().trim() ?? '')
                .where((question) => question.isNotEmpty)
                .toList()
            : <String>[];
        if (questions.isNotEmpty) {
          return questions;
        }
      }
    } catch (e) {
      debugPrint('No se pudieron obtener preguntas sugeridas: $e');
    }

    return List<String>.from(_fallbackQuickReplies);
  }

  Future<AmbiguousQuestionWarning?> checkAmbiguousQuestion(String question) async {
    final normalized = question.toLowerCase();

    if (kDebugMode) {
      for (final entry in _debugAmbiguousRules.entries) {
        if (normalized.contains(entry.key)) {
          return AmbiguousQuestionWarning(
            title: entry.value['title']!,
            message: entry.value['message']!,
            relatedQuestion: entry.value['relatedQuestion'],
          );
        }
      }
      return null;
    }

    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/chat/ambiguity-check'),
        headers: {'Content-Type': 'application/json; charset=UTF-8'},
        body: jsonEncode({'question': question}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final shouldWarn = data['shouldWarn'] as bool? ?? false;
        if (shouldWarn) {
          return AmbiguousQuestionWarning.fromJson(data);
        }
      }
    } catch (e) {
      debugPrint('No se pudo validar ambigüedad de la pregunta: $e');
    }

    return null;
  }

  // Método para enviar una pregunta al backend Flask
  Future<String> askQuestion(String question) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/ask'),
        headers: {
          'Content-Type': 'application/json; charset=UTF-8',
        },
        body: jsonEncode(<String, String>{
          'question': question,
        }),
      );

      if (response.statusCode == 200) {
        final Map<String, dynamic> responseData = jsonDecode(response.body);
        return responseData['answer'] ?? 'No se recibió una respuesta válida.';
      } else {
        // Manejar errores de la API de forma más detallada
        debugPrint('Error de API (${response.statusCode}): ${response.body}');
        if (response.statusCode == 400) {
          return 'Error: La pregunta no pudo ser procesada. Revisa tu consulta.';
        } else if (response.statusCode == 500) {
          return 'Error del servidor. Por favor, inténtalo más tarde.';
        } else {
          return 'Ocurrió un error desconocido.';
        }
      }
    } catch (e) {
      debugPrint('Excepción al hacer la llamada a la API: $e');
      return 'No se pudo conectar con el servidor. Asegúrate de que el backend esté corriendo.';
    }
  }

  // Puedes añadir otros métodos aquí si necesitas obtener datos del backend
  // Future<List<dynamic>> getTransactions() async { ... }

  // ── Login ──────────────────────────────────────────────────────────────────
  // Llama a POST /auth/login con username y password.
  // Devuelve un [UserModel] si la respuesta es 200, o lanza una [Exception]
  // con el mensaje de error para mostrarlo en la UI.
  //
  // TODO: ajustar el endpoint y los campos del JSON cuando el backend esté listo.
  Future<UserModel> login(String username, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/auth/login'),
        headers: {'Content-Type': 'application/json; charset=UTF-8'},
        body: jsonEncode({
          'username': username.trim(),
          'password': password,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return UserModel.fromJson(data);
      } else if (response.statusCode == 400) {
        throw Exception('Ingresa tu usuario.');
      } else {
        throw Exception('Error del servidor (${response.statusCode}). Intenta más tarde.');
      }
    } catch (e) {
      if (e is Exception) rethrow;
      throw Exception('No se pudo conectar al servidor.');
    }
  }
}