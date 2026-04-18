import 'package:flutter/material.dart';
import '../core/api_service.dart';

// ── Modelo de mensaje ──────────────────────────────────────────────────────────
class ChatMessage {
  final String text;
  final bool isUser;
  final DateTime timestamp;

  ChatMessage({
    required this.text,
    required this.isUser,
    required this.timestamp,
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
  final List<String> _visibleQuickReplies = [];
  bool _isLoading = false;

  static const double _itemHeight = 52.0;
  static const double _itemSeparator = 8.0;

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
      _visibleQuickReplies
        ..clear()
        ..addAll(randomized.take(3));
    });
  }

  String _sanitizeInput(Object? value) {
    return value?.toString().trim() ?? '';
  }

  Future<void> _handleMessageSubmit(Object? text) async {
    final trimmed = _sanitizeInput(text);
    if (trimmed.isEmpty || _isLoading) return;

    final warning = await _apiService.checkAmbiguousQuestion(trimmed);
    if (!mounted) return;

    if (warning != null) {
      final shouldContinue = await _showAmbiguityWarning(warning);
      if (shouldContinue != true) return;
    }

    await _sendMessage(trimmed);
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

  Future<void> _sendMessage(Object? text) async {
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

    setState(() {
      _messages.add(ChatMessage(text: response, isUser: false, timestamp: DateTime.now()));
      _isLoading = false;
    });
    _scrollToBottom();
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
      toolbarHeight: 66,
      titleSpacing: 10,
      title: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          CircleAvatar(
            radius: 27,
            backgroundColor: Colors.white24,
            child: const Icon(Icons.smart_toy_rounded, color: Colors.white, size: 32),
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
        return _buildMessageBubble(_messages[index]);
      },
    );
  }

  Widget _buildMessageBubble(ChatMessage message) {
    final isUser = message.isUser;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!isUser) ...[
            CircleAvatar(
              radius: 16,
              backgroundColor: _brandColor,
              child: const Icon(Icons.smart_toy_rounded, color: Colors.white, size: 16),
            ),
            const SizedBox(width: 6),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: isUser ? _brandColor : Colors.white,
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(18),
                  topRight: const Radius.circular(18),
                  bottomLeft: Radius.circular(isUser ? 18 : 4),
                  bottomRight: Radius.circular(isUser ? 4 : 18),
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
                style: TextStyle(
                  color: isUser ? Colors.white : const Color(0xFF1F2937),
                  fontSize: 20,
                  height: 1.4,
                ),
              ),
            ),
          ),
          if (isUser) const SizedBox(width: 6),
        ],
      ),
    );
  }

  Widget _buildTypingIndicator() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          CircleAvatar(
            radius: 16,
            backgroundColor: _brandColor,
            child: const Icon(Icons.smart_toy_rounded, color: Colors.white, size: 16),
          ),
          const SizedBox(width: 6),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(18),
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
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 4),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (var index = 0; index < _visibleQuickReplies.length; index++) ...[
            _QuickReplyItem(
              text: _visibleQuickReplies[index],
              disabled: _isLoading,
              onTap: () => _handleMessageSubmit(_visibleQuickReplies[index]),
            ),
            if (index != _visibleQuickReplies.length - 1)
              SizedBox(height: _itemSeparator),
          ],
        ],
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
  });

  final String text;
  final VoidCallback onTap;
  final bool disabled;

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
    final maxBubbleWidth = screenWidth * 0.82;
    final fontSize = screenWidth < 380 ? 14.5 : 16.0;

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
                      minHeight: _ChatScreenState._itemHeight,
                    ),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
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
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
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
