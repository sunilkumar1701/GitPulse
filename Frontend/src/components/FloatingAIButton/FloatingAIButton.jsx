import React, { useState, useRef, useCallback } from 'react';
import chatbotIcon from '../../assets/Chatbot.png';
import ChatPanel from '../chat/ChatPanel';
import './FloatingAIButton.css';

const FloatingAIButton = ({ username }) => {
  const [showChatbot, setShowChatbot] = useState(false);
  const [position, setPosition] = useState({ x: 20, y: 20 }); // Bottom right offset
  const [isDragging, setIsDragging] = useState(false); // purely for CSS
  
  const dragStartRef = useRef({ x: 0, y: 0 });
  const isDraggingRef = useRef(false); // synchronous tracking
  const buttonRef = useRef(null);

  const toggleChatbot = (e) => {
    // Only toggle if we didn't just finish dragging
    if (!isDraggingRef.current) {
      setShowChatbot((prev) => !prev);
    }
  };

  const handlePointerDown = (e) => {
    // Left mouse button or touch
    if (e.button !== 0 && e.type !== 'touchstart') return;

    isDraggingRef.current = false;
    setIsDragging(false);

    const clientX = e.type === 'touchstart' ? e.touches[0].clientX : e.clientX;
    const clientY = e.type === 'touchstart' ? e.touches[0].clientY : e.clientY;

    dragStartRef.current = {
      x: clientX,
      y: clientY,
    };

    document.addEventListener('pointermove', handlePointerMove);
    document.addEventListener('pointerup', handlePointerUp);
    // for touch devices fallback
    document.addEventListener('touchmove', handlePointerMove, { passive: false });
    document.addEventListener('touchend', handlePointerUp);
  };

  const handlePointerMove = useCallback((e) => {
    const clientX = e.type === 'touchmove' ? e.touches[0].clientX : e.clientX;
    const clientY = e.type === 'touchmove' ? e.touches[0].clientY : e.clientY;

    if (!isDraggingRef.current) {
        // If movement is significant, start dragging immediately
        const dx = Math.abs(clientX - dragStartRef.current.x);
        const dy = Math.abs(clientY - dragStartRef.current.y);
        if (dx > 5 || dy > 5) {
            isDraggingRef.current = true;
            setIsDragging(true);
        } else {
            return;
        }
    }

    if (e.type === 'touchmove') {
      e.preventDefault(); // Prevent scrolling while dragging
    }

    const deltaX = clientX - dragStartRef.current.x;
    const deltaY = clientY - dragStartRef.current.y;

    setPosition((prev) => {
      // Calculate new position but keep it within screen bounds
      let newX = prev.x - deltaX;
      let newY = prev.y - deltaY;

      const maxX = window.innerWidth - 60;
      const maxY = window.innerHeight - 60;

      newX = Math.max(0, Math.min(newX, maxX));
      newY = Math.max(0, Math.min(newY, maxY));

      return { x: newX, y: newY };
    });

    dragStartRef.current.x = clientX;
    dragStartRef.current.y = clientY;
  }, [isDragging]);

  const handlePointerUp = useCallback(() => {
    // Slight delay to prevent click event right after drop
    setTimeout(() => {
      isDraggingRef.current = false;
      setIsDragging(false);
    }, 50);

    document.removeEventListener('pointermove', handlePointerMove);
    document.removeEventListener('pointerup', handlePointerUp);
    document.removeEventListener('touchmove', handlePointerMove);
    document.removeEventListener('touchend', handlePointerUp);
  }, [handlePointerMove]);

  return (
    <>
      <button
        ref={buttonRef}
        className={`floating-ai-btn ${isDragging ? 'dragging' : ''}`}
        style={{ right: `${position.x}px`, bottom: `${position.y}px` }}
        onPointerDown={handlePointerDown}
        onClick={toggleChatbot}
        title="GitHub AI Assistant"
        aria-label="Toggle GitHub AI Assistant"
      >
        <img src={chatbotIcon} alt="AI Assistant" className="floating-ai-image" draggable={false} />
      </button>

      {showChatbot && (
        <ChatPanel
          onClose={() => setShowChatbot(false)}
          username={username}
        />
      )}
    </>
  );
};

export default FloatingAIButton;
