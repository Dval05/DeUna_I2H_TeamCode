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
  final ScrollController _quickScrollController = ScrollController();
  final ApiService _apiService = ApiService();
  bool _isLoading = false;
  bool _isQuickRepliesAtBottom = false;

  static const double _itemHeight = 52.0;
  static const double _itemSeparator = 8.0;

  // Preguntas rápidas predefinidas
  static const List<String> _quickReplies = [
    '¿Qué servicios ofrecen?',
    '¿Cómo puedo hacer un pago?',
    '¿Cuáles son los horarios de atención?',
    '¿Cómo creo una cuenta?',
    '¿Cómo reporto un problema?',
  ];

  static const Color _brandColor = Color(0xFF5B21B6);

  @override
  void initState() {
    super.initState();
    _quickScrollController.addListener(_updateQuickRepliesPosition);
    _messages.add(ChatMessage(
      text: '¡Hola! Soy tu asistente virtual de DeUna 👋\n¿En qué puedo ayudarte hoy?',
      isUser: false,
      timestamp: DateTime.now(),
    ));
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _updateQuickRepliesPosition();
      }
    });
  }

  @override
  void dispose() {
    _quickScrollController.removeListener(_updateQuickRepliesPosition);
    _controller.dispose();
    _scrollController.dispose();
    _quickScrollController.dispose();
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

  void _updateQuickRepliesPosition() {
    if (!_quickScrollController.hasClients) return;
    final position = _quickScrollController.position;
    if (!position.hasContentDimensions) return;

    final atBottom =
        position.maxScrollExtent > 0 && position.pixels >= position.maxScrollExtent;

    if (_isQuickRepliesAtBottom != atBottom && mounted) {
      setState(() {
        _isQuickRepliesAtBottom = atBottom;
      });
    }
  }

  Future<void> _sendMessage(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty || _isLoading) return;

    setState(() {
      _messages.add(ChatMessage(text: trimmed, isUser: true, timestamp: DateTime.now()));
      _isLoading = true;
    });
    _controller.clear();
    _scrollToBottom();

    final response = await _apiService.askQuestion(trimmed);

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
      body: Column(
        children: [
          Expanded(child: _buildMessageList()),
          _buildQuickReplies(),
          _buildInputBar(),
        ],
      ),
    );
  }

  PreferredSizeWidget _buildAppBar() {
    return AppBar(
      backgroundColor: _brandColor,
      foregroundColor: Colors.white,
      elevation: 0,
      title: Row(
        children: [
          CircleAvatar(
            radius: 18,
            backgroundColor: Colors.white24,
            child: const Icon(Icons.smart_toy_rounded, color: Colors.white, size: 20),
          ),
          const SizedBox(width: 10),
          const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Asistente DeUna',
                style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
              ),
              Text(
                '● En línea',
                style: TextStyle(fontSize: 11, color: Color(0xFF86EFAC)),
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
                  fontSize: 14.5,
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
  void _scrollQuickReplies() {
    if (!_quickScrollController.hasClients) return;
    final step = _itemHeight + _itemSeparator;
    final max = _quickScrollController.position.maxScrollExtent;
    final next = _quickScrollController.offset + step;
    _quickScrollController.animateTo(
      next > max ? 0 : next,
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeOut,
    );
  }

  Widget _buildQuickReplies() {
    const visibleCount = 3;
    final listHeight =
        visibleCount * _itemHeight + (visibleCount - 1) * _itemSeparator;

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 4),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(
            height: listHeight,
            child: ListView.separated(
              controller: _quickScrollController,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _quickReplies.length,
              separatorBuilder: (context, index) =>
                  SizedBox(height: _itemSeparator),
              itemBuilder: (context, index) => SizedBox(
                height: _itemHeight,
                child: _QuickReplyItem(
                  text: _quickReplies[index],
                  disabled: _isLoading,
                  onTap: () => _sendMessage(_quickReplies[index]),
                ),
              ),
            ),
          ),
          GestureDetector(
            onTap: _scrollQuickReplies,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Icon(
                _isQuickRepliesAtBottom
                    ? Icons.keyboard_arrow_up_rounded
                    : Icons.keyboard_arrow_down_rounded,
                color: _brandColor.withValues(alpha: 0.55),
                size: 26,
              ),
            ),
          ),
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
                    onSubmitted: _sendMessage,
                    decoration: InputDecoration(
                      hintText: 'Escribe tu pregunta...',
                      hintStyle: TextStyle(color: Colors.grey.shade400),
                      filled: true,
                      fillColor: Colors.transparent,
                      contentPadding:
                          const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
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
                onTap: _isLoading ? null : () => _sendMessage(_controller.text),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  width: 44,
                  height: 44,
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
                    size: 20,
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
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        GestureDetector(
          onTap: _handleTap,
          child: AnimatedBuilder(
            animation: _borderOpacity,
            builder: (context, child) {
              return Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 0),
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
                  style: TextStyle(
                    color: widget.disabled ? Colors.grey : _brandColor,
                    fontSize: 13.5,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}
