import { Avatar, AvatarFallback } from './ui/avatar';

/**
 * @typedef {Object} ChatMessageProps
 * @property {'user' | 'assistant'} role
 * @property {string} content
 * @property {string} [timestamp]
 * @property {string|null} [image]
 * @property {string|null} [tool]
 */

/**
 * Component for rendering a single chat message
 * @param {ChatMessageProps} props
 */
export function ChatMessage({ role, content, timestamp, image, tool }) {
  const isUser = role === 'user';

  if (isUser) {
    // User messages - right aligned
    return (
      <div className="flex gap-4 p-6 justify-end">
        <div className="flex flex-col items-end max-w-[75%]">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-foreground text-sm font-medium">
              You
            </span>
            {timestamp && (
              <span className="text-muted-foreground text-xs">
                {timestamp}
              </span>
            )}
          </div>
          
          <div className="bg-primary text-primary-foreground rounded-lg rounded-tr-sm p-4 break-words overflow-hidden w-fit max-w-full">
            {content}
          </div>
        </div>
        
        <Avatar className="h-8 w-8 flex-shrink-0">
          <AvatarFallback className="bg-primary text-primary-foreground">
            U
          </AvatarFallback>
        </Avatar>
      </div>
    );
  }

  // Assistant messages - left aligned
  return (
    <div className="flex gap-4 p-6">
      <Avatar className="h-8 w-8 flex-shrink-0">
        <AvatarFallback className="bg-accent text-accent-foreground">
          AI
        </AvatarFallback>
      </Avatar>
      
      <div className="flex flex-col max-w-[75%]">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-foreground text-sm font-medium">
            Assistant
          </span>
          {timestamp && (
            <span className="text-muted-foreground text-xs">
              {timestamp}
            </span>
          )}
        </div>
        
        <div className="bg-card border border-border text-foreground rounded-lg rounded-tl-sm p-4 break-words overflow-hidden w-fit max-w-full">
          {content}
          
          {image && (
            <div className="mt-3">
              <img 
                src={image} 
                alt="Generated content" 
                className="rounded-md max-w-full max-h-[300px] object-contain"
              />
            </div>
          )}
          
          {tool && tool !== 'conversation' && (
            <div className="mt-2 text-xs text-muted-foreground">
              Tool used: {tool}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
