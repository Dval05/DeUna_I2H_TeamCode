import 'package:flutter/material.dart';
import '../core/api_service.dart';

// ── Modelo de mensaje ──────────────────────────────────────────────────────────
class ChatMessage {
  final String text;
  final bool isUser;
  final DateTime timestamp;
  final bool isError;
  final List<String> suggestedQuestions;
  final bool showDiscountPrompt;

  ChatMessage({
    required this.text,
    required this.isUser,
    required this.timestamp,
    this.isError = false,
    this.suggestedQuestions = const [],
    this.showDiscountPrompt = false,
  });
}

// ── Pantalla principal ─────────────────────────────────────────────────────────
class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final List<ChatMessage> _messages = [];
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final ApiService _apiService = ApiService();
  final List<String> _allSuggestedQuestions = [];
  final List<String> _visibleQuickReplies = [];
  final Set<int> _dismissedDiscountPrompts = {};
  bool _isLoading = false;

  static const double _itemHeight = 52.0;
  static const double _itemSeparator = 8.0;
  static const String _botAvatarAsset = 'lib/images/uno mascota.png';
  static const String _sadBotAsset = 'lib/images/triste.png';
  
  // Ajusta estos valores para controlar facilmente los tamanos de las imagenes.
  static const double _profileAvatarImageSize = 200;
  static const double _errorImageViewportFactor = 0.34;
  static const double _errorImageMinHeight = 180.0;
  static const double _errorImageMaxHeight = 320.0;

  static const Color _brandColor = Color(0xFF5B21B6);

  @override
  void initState() {
    super.initState();
    _messages.add(ChatMessage(
      text: '¡Hola! Soy tu asistente virtual de DeUna 👋\n¿En qué puedo ayudarte hoy?',
      isUser: false,
      timestamp: DateTime.now(),
    ));
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _loadQuickReplies();
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _loadQuickReplies() async {
    final suggestions = await _apiService.fetchSuggestedQuestions();
    if (!mounted) return;

    final randomized = List<String>.of(suggestions)..shuffle();
    setState(() {
      _allSuggestedQuestions
        ..clear()
        ..addAll(suggestions);
      _visibleQuickReplies
        ..clear()
        ..addAll(randomized.take(3));
    });
  }

  String _sanitizeInput(Object? value) {
    return value?.toString().trim() ?? '';
  }

  Future<void> _handleMessageSubmit(
    Object? text, {
    bool fromQuickReply = false,
  }) async {
    final trimmed = _sanitizeInput(text);
    if (trimmed.isEmpty || _isLoading) return;

    List<String>? previousQuickReplies;
    if (fromQuickReply) {
      previousQuickReplies = List<String>.of(_visibleQuickReplies);
      setState(() {
        _visibleQuickReplies.clear();
      });
    }

    final warning = await _apiService.checkAmbiguousQuestion(trimmed);
    if (!mounted) return;

    if (warning != null) {
      final shouldContinue = await _showAmbiguityWarning(warning);
      if (shouldContinue != true) {
        if (fromQuickReply && previousQuickReplies != null) {
          setState(() {
            _visibleQuickReplies
              ..clear()
              ..addAll(previousQuickReplies!);
          });
        }
        return;
      }
    }

    await _sendMessage(trimmed, fromQuickReply: fromQuickReply);
  }

  Future<bool?> _showAmbiguityWarning(AmbiguousQuestionWarning warning) {
    return showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text(warning.title),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(warning.message),
              if (warning.relatedQuestion != null) ...[
                const SizedBox(height: 12),
                Text(
                  'Ejemplo relacionado: ${warning.relatedQuestion}',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ],
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Editar'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Enviar igual'),
            ),
          ],
        );
      },
    );
  }

  Future<void> _sendMessage(
    Object? text, {
    bool fromQuickReply = false,
  }) async {
    final trimmed = _sanitizeInput(text);
    if (trimmed.isEmpty || _isLoading) return;

    setState(() {
      _messages.add(ChatMessage(text: trimmed, isUser: true, timestamp: DateTime.now()));
      _isLoading = true;
    });
    _controller.clear();
    _scrollToBottom();

    final response = await _apiService.askQuestion(trimmed);
    if (!mounted) return;

    final isErrorResponse = _isChatbotError(response);
    final nextQuickReplies = isErrorResponse
        ? <String>[]
        : (fromQuickReply ? _buildRelatedQuickReply(trimmed) : List<String>.of(_visibleQuickReplies));
    final errorSuggestions = isErrorResponse
        ? _buildErrorSuggestions(trimmed)
        : const <String>[];

    setState(() {
      _messages.add(
        ChatMessage(
          text: response,
          isUser: false,
          timestamp: DateTime.now(),
          isError: isErrorResponse,
          suggestedQuestions: errorSuggestions,
          showDiscountPrompt: !isErrorResponse && _isClientRelatedQuestion(trimmed),
        ),
      );
      _visibleQuickReplies
        ..clear()
        ..addAll(nextQuickReplies);
      _isLoading = false;
    });
    _scrollToBottom();
  }

  bool _isChatbotError(String response) {
    const knownErrorPrefixes = [
      'Error:',
      'Error del servidor',
      'No se pudo conectar con el servidor',
      'Ocurrió un error desconocido.',
    ];

    return knownErrorPrefixes.any(response.startsWith);
  }

  bool _isClientRelatedQuestion(String question) {
    const clientKeywords = [
      'cliente',
      'clientes',
      'dinero',
      'mes',
      'compra',
      'ventas',
      'venta',
      'gasto',
      'gastos',
      'nuevo',
      'nuevos',
      'pago',
      'factura',
      'inactivo',
      'activo',
    ];
    final lower = question.toLowerCase();
    return clientKeywords.any(lower.contains);
  }

  List<String> _buildRelatedQuickReply(String question) {
    final related = _pickBestRelatedQuestion(question);
    if (related == null) {
      return const [];
    }
    return [related];
  }

  List<String> _buildErrorSuggestions(String question) {
    final ranked = _rankQuestionsByRelation(question);
    if (ranked.isNotEmpty) {
      return ranked.take(5).toList();
    }

    return _allSuggestedQuestions.take(5).toList();
  }

  String? _pickBestRelatedQuestion(String question) {
    final ranked = _rankQuestionsByRelation(question);
    if (ranked.isEmpty) {
      return null;
    }
    return ranked.first;
  }

  List<String> _rankQuestionsByRelation(String question) {
    final baseWords = _keywordsFor(question);
    final ranked = _allSuggestedQuestions
        .where((candidate) => candidate.trim().isNotEmpty)
        .where((candidate) => candidate.trim() != question.trim())
        .map((candidate) => (
              question: candidate,
              score: _scoreQuestionRelation(baseWords, candidate),
            ))
        .toList()
      ..sort((left, right) {
        final scoreComparison = right.score.compareTo(left.score);
        if (scoreComparison != 0) {
          return scoreComparison;
        }
        return left.question.length.compareTo(right.question.length);
      });

    final positiveScores = ranked.where((entry) => entry.score > 0).map((entry) => entry.question).toList();
    if (positiveScores.isNotEmpty) {
      return positiveScores;
    }

    return ranked.map((entry) => entry.question).toList();
  }

  Set<String> _keywordsFor(String text) {
    const stopWords = {
      'que',
      'qué',
      'como',
      'cómo',
      'cuanto',
      'cuánta',
      'cuánto',
      'cuantos',
      'cuántos',
      'cual',
      'cuál',
      'cuales',
      'cuáles',
      'del',
      'de',
      'la',
      'el',
      'los',
      'las',
      'mi',
      'me',
      'en',
      'por',
      'vs',
      'esta',
      'este',
      'hoy',
      'una',
      'uno',
      'unos',
      'unas',
      'para',
      'con',
      'mas',
      'más',
      'ya',
      'lo',
      'es',
      'se',
      'ha',
      'he',
      'a',
      'y',
      'o',
    };

    return text
        .toLowerCase()
        .replaceAll(RegExp(r'[^a-záéíóúñ0-9 ]', unicode: true), ' ')
        .split(RegExp(r'\s+'))
        .where((word) => word.length > 2)
        .where((word) => !stopWords.contains(word))
        .toSet();
  }

  int _scoreQuestionRelation(Set<String> baseWords, String candidate) {
    final candidateWords = _keywordsFor(candidate);
    if (baseWords.isEmpty || candidateWords.isEmpty) {
      return 0;
    }

    return candidateWords.where(baseWords.contains).length;
  }

  Widget _buildProfileBotAvatar({
    required double imageSize,
  }) {
    return SizedBox(
      width: 70,
      height: 84,
      child: OverflowBox(
        maxWidth: imageSize,
        maxHeight: imageSize,
        alignment: Alignment(0.1, 0),
        child: Image.asset(
          _botAvatarAsset,
          width: imageSize,
          height: imageSize,
          fit: BoxFit.scaleDown,
        ),
      ),
    );
  }



  // ── Build ──────────────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF0F4F8),
      appBar: _buildAppBar(),
      body: Stack(
        children: [
          _buildBackgroundLogo(),
          Column(
            children: [
              Expanded(child: _buildMessageList()),
              _buildQuickReplies(),
              _buildInputBar(),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildBackgroundLogo() {
    return IgnorePointer(
      child: Align(
        alignment: const Alignment(0, -0.12),
        child: Opacity(
          opacity: 0.3,
          child: Image.asset(
            'lib/images/deunalogo.png',
            width: 400,
            fit: BoxFit.contain,
          ),
        ),
      ),
    );
  }

  PreferredSizeWidget _buildAppBar() {
    return AppBar(
      backgroundColor: _brandColor,
      foregroundColor: Colors.white,
      elevation: 0,
      toolbarHeight: 84,
      titleSpacing: 10,
      title: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          _buildProfileBotAvatar(
            imageSize: _profileAvatarImageSize,
          ),
          const SizedBox(width: 12),
          const Column(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Asistente DeUna',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              Text(
                '● En línea',
                style: TextStyle(fontSize: 15, color: Color(0xFF86EFAC)),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMessageList() {
    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 12),
      itemCount: _messages.length + (_isLoading ? 1 : 0),
      itemBuilder: (context, index) {
        if (index == _messages.length) return _buildTypingIndicator();
        return _buildMessageBubble(_messages[index], index);
      },
    );
  }

  Widget _buildMessageBubble(ChatMessage message, int messageIndex) {
    final isUser = message.isUser;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Flexible(
            child: isUser
                ? Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        decoration: BoxDecoration(
                          color: _brandColor,
                          borderRadius: const BorderRadius.only(
                            topLeft: Radius.circular(18),
                            topRight: Radius.circular(18),
                            bottomLeft: Radius.circular(18),
                            bottomRight: Radius.circular(4),
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.06),
                              blurRadius: 4,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: Text(
                          message.text,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 20,
                            height: 1.4,
                          ),
                        ),
                      ),
                    ],
                  )
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.fromLTRB(20, 14, 14, 10),
                        decoration: BoxDecoration(
                          color: message.isError
                              ? const Color(0xFFFFF1F2)
                              : Colors.white,
                          borderRadius: const BorderRadius.only(
                            topLeft: Radius.circular(24),
                            topRight: Radius.circular(18),
                            bottomLeft: Radius.circular(4),
                            bottomRight: Radius.circular(18),
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.06),
                              blurRadius: 4,
                              offset: const Offset(0, 2),
                            ),
                          ],
                          border: message.isError
                              ? Border.all(color: const Color(0xFFFDA4AF), width: 1)
                              : null,
                        ),
                        child: Text(
                          message.text,
                          style: const TextStyle(
                            color: Color(0xFF1F2937),
                            fontSize: 20,
                            height: 1.4,
                          ),
                        ),
                      ),
                      if (message.isError) ...[
                        const SizedBox(height: 10),
                        _buildErrorPanel(message),
                      ],
                      if (message.showDiscountPrompt && !_dismissedDiscountPrompts.contains(messageIndex)) ...[
                        const SizedBox(height: 10),
                        _buildDiscountPromptBubble(messageIndex),
                      ],
                    ],
                  ),
          ),
          if (isUser) const SizedBox(width: 6),
        ],
      ),
    );
  }

  Widget _buildDiscountPromptBubble(int messageIndex) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
        ],
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Image.asset(
              'lib/images/duda.png',
              height: 100,
              fit: BoxFit.contain,
            ),
          ),
          const SizedBox(height: 12),
          const Text(
            'Tu cliente X no ha comprado nada durante un tiempo. '
            '¿Quieres ofrecerle un cupón de \$5 de descuento en su siguiente compra mayor a \$15?',
            style: TextStyle(
              color: Color(0xFF1F2937),
              fontSize: 16,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 14),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton(
                onPressed: () {
                  setState(() => _dismissedDiscountPrompts.add(messageIndex));
                },
                child: const Text(
                  'No',
                  style: TextStyle(fontSize: 15, color: Color(0xFF6B7280)),
                ),
              ),
              const SizedBox(width: 8),
              FilledButton(
                style: FilledButton.styleFrom(backgroundColor: _brandColor),
                onPressed: () {
                  setState(() => _dismissedDiscountPrompts.add(messageIndex));
                  _showDiscountAcceptedDialog();
                },
                child: const Text('Sí', style: TextStyle(fontSize: 15)),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Future<void> _showDiscountAcceptedDialog() {
    return showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text(
          '¡Entendido!',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        content: Image.asset(
          'lib/images/alegre.png',
          height: 200,
          fit: BoxFit.contain,
        ),
        actions: [
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: _brandColor),
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cerrar'),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorPanel(ChatMessage message) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final imageHeight =
          MediaQuery.of(context).size.height * _errorImageViewportFactor;
        return Container(
          width: double.infinity,
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 12),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.96),
            borderRadius: BorderRadius.circular(18),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.05),
                blurRadius: 6,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Image.asset(
                  _sadBotAsset,
                  height: imageHeight.clamp(
                    _errorImageMinHeight,
                    _errorImageMaxHeight,
                  ),
                  fit: BoxFit.contain,
                ),
              ),
              const SizedBox(height: 10),
              const Text(
                'Prueba con estas preguntas:',
                style: TextStyle(
                  color: Color(0xFF374151),
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 12),
              _ErrorSuggestionCarousel(
                questions: message.suggestedQuestions,
                maxWidth: constraints.maxWidth,
                disabled: _isLoading,
                onSelect: (question) => _handleMessageSubmit(question, fromQuickReply: true),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildTypingIndicator() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(24),
                topRight: Radius.circular(18),
                bottomRight: Radius.circular(18),
                bottomLeft: Radius.circular(4),
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.06),
                  blurRadius: 4,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: const SizedBox(
              width: 40,
              height: 14,
              child: _TypingDots(),
            ),
          ),
        ],
      ),
    );
  }

  // ── Quick replies ──────────────────────────────────────────────────────────
  Widget _buildQuickReplies() {
    if (_visibleQuickReplies.isEmpty) {
      return const SizedBox.shrink();
    }

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 6),
      child: AnimatedSwitcher(
        duration: const Duration(milliseconds: 260),
        switchInCurve: Curves.easeOutCubic,
        switchOutCurve: Curves.easeInCubic,
        child: LayoutBuilder(
          key: ValueKey(_visibleQuickReplies.join('|')),
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 430;
            return Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (var index = 0; index < _visibleQuickReplies.length; index++) ...[
                  _QuickReplyItem(
                    text: _visibleQuickReplies[index],
                    disabled: _isLoading,
                    compact: compact,
                    onTap: () => _handleMessageSubmit(
                      _visibleQuickReplies[index],
                      fromQuickReply: true,
                    ),
                  ),
                  if (index != _visibleQuickReplies.length - 1)
                    SizedBox(height: compact ? 6 : _itemSeparator),
                ],
              ],
            );
          },
        ),
      ),
    );
  }

  // ── Input bar (flotante, sin fondo blanco) ──────────────────────────────────
  Widget _buildInputBar() {
    return Container(
      color: Colors.transparent,
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 4, 12, 12),
          child: Row(
            children: [
              Expanded(
                child: Container(
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(24),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.08),
                        blurRadius: 10,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: TextField(
                    controller: _controller,
                    enabled: !_isLoading,
                    textCapitalization: TextCapitalization.sentences,
                    onSubmitted: _handleMessageSubmit,
                    decoration: InputDecoration(
                      hintText: 'Escribe tu pregunta...',
                      hintStyle: TextStyle(
                        color: Colors.grey.shade400,
                        fontSize: 20,
                      ),
                      filled: true,
                      fillColor: Colors.transparent,
                      contentPadding:
                          const EdgeInsets.symmetric(horizontal: 16, vertical: 17),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide.none,
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              GestureDetector(
                onTap: _isLoading ? null : () => _handleMessageSubmit(_controller.text),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  width: 44,
                  height: 60,
                  decoration: BoxDecoration(
                    color: _isLoading ? Colors.grey.shade300 : _brandColor,
                    shape: BoxShape.circle,
                    boxShadow: _isLoading
                        ? []
                        : [
                            BoxShadow(
                              color: _brandColor.withValues(alpha: 0.35),
                              blurRadius: 8,
                              offset: const Offset(0, 3),
                            ),
                          ],
                  ),
                  child: Icon(
                    Icons.send_rounded,
                    color: _isLoading ? Colors.grey : Colors.white,
                    size: 30,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Animación de puntos "escribiendo..." ───────────────────────────────────────
class _TypingDots extends StatefulWidget {
  const _TypingDots();

  @override
  State<_TypingDots> createState() => _TypingDotsState();
}

class _TypingDotsState extends State<_TypingDots>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        return Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: List.generate(3, (i) {
            final t = (_controller.value + i / 3) % 1.0;
            final opacity = t < 0.5 ? t * 2 : 1 - (t - 0.5) * 2;
            return Opacity(
              opacity: 0.3 + opacity * 0.7,
              child: Container(
                width: 7,
                height: 7,
                decoration: const BoxDecoration(
                  color: Color(0xFF5B21B6),
                  shape: BoxShape.circle,
                ),
              ),
            );
          }),
        );
      },
    );
  }
}

// ── Ítem de pregunta rápida con borde animado ─────────────────────────────────
class _QuickReplyItem extends StatefulWidget {
  const _QuickReplyItem({
    required this.text,
    required this.onTap,
    required this.disabled,
    required this.compact,
  });

  final String text;
  final VoidCallback onTap;
  final bool disabled;
  final bool compact;

  @override
  State<_QuickReplyItem> createState() => _QuickReplyItemState();
}

class _QuickReplyItemState extends State<_QuickReplyItem>
    with SingleTickerProviderStateMixin {
  static const Color _brandColor = Color(0xFF5B21B6);
  late AnimationController _borderCtrl;
  late Animation<double> _borderOpacity;

  @override
  void initState() {
    super.initState();
    _borderCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 220),
    );
    _borderOpacity = Tween<double>(begin: 1.0, end: 0.0).animate(
      CurvedAnimation(parent: _borderCtrl, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _borderCtrl.dispose();
    super.dispose();
  }

  Future<void> _handleTap() async {
    if (widget.disabled) return;
    // Border flashes out → back in to confirm selection
    await _borderCtrl.forward();
    if (!mounted) return;
    await _borderCtrl.reverse();
    if (!mounted) return;
    widget.onTap();
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final maxBubbleWidth = widget.compact ? screenWidth * 0.92 : screenWidth * 0.82;
    final fontSize = widget.compact ? 14.2 : (screenWidth < 380 ? 14.5 : 16.0);

    return Row(
      mainAxisSize: MainAxisSize.max,
      children: [
        Flexible(
          child: Align(
            alignment: Alignment.centerLeft,
            child: GestureDetector(
              onTap: _handleTap,
              child: AnimatedBuilder(
                animation: _borderOpacity,
                builder: (context, child) {
                  return ConstrainedBox(
                    constraints: BoxConstraints(
                      maxWidth: maxBubbleWidth,
                      minHeight: widget.compact ? 46 : _ChatScreenState._itemHeight,
                    ),
                    child: Container(
                      padding: EdgeInsets.symmetric(
                        horizontal: widget.compact ? 14 : 16,
                        vertical: widget.compact ? 9 : 10,
                      ),
                      decoration: BoxDecoration(
                        color: widget.disabled
                            ? Colors.grey.shade100
                            : Colors.white.withValues(alpha: 0.92),
                        borderRadius: BorderRadius.circular(30),
                        border: Border.all(
                          color: widget.disabled
                              ? Colors.grey.shade300
                              : _brandColor.withValues(alpha: _borderOpacity.value),
                          width: 0.5,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.05),
                            blurRadius: 6,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      alignment: Alignment.centerLeft,
                      child: Text(
                        widget.text,
                        softWrap: true,
                        maxLines: widget.compact ? 4 : 3,
                        overflow: TextOverflow.fade,
                        style: TextStyle(
                          color: widget.disabled ? Colors.grey : _brandColor,
                          fontSize: fontSize,
                          fontWeight: FontWeight.w500,
                          height: 1.25,
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _ErrorSuggestionCarousel extends StatelessWidget {
  const _ErrorSuggestionCarousel({
    required this.questions,
    required this.maxWidth,
    required this.disabled,
    required this.onSelect,
  });

  final List<String> questions;
  final double maxWidth;
  final bool disabled;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) {
    if (questions.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      children: [
        for (var i = 0; i < questions.length; i++) ...[
          InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: disabled ? null : () => onSelect(questions[i]),
            child: Ink(
              decoration: BoxDecoration(
                color: const Color(0xFFF3F4F6),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    questions[i],
                    style: const TextStyle(
                      color: Color(0xFF0F766E),
                      fontSize: 15,
                      fontWeight: FontWeight.w500,
                      height: 1.4,
                    ),
                  ),
                ),
              ),
            ),
          ),
          if (i < questions.length - 1) const SizedBox(height: 8),
        ],
      ],
    );
  }
}
