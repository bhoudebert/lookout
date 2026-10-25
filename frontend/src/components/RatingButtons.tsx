import type { Rating } from "../api/types";

interface Props {
  rating: number;
  /** The item's title, so a screen reader knows which item a thumb belongs to. */
  about: string;
  onRate: (rating: Exclude<Rating, 0>) => void;
}

/** Thumbs up and down. A pressed thumb is the item's rating; pressing it again clears it. */
export function RatingButtons({ rating, about, onRate }: Props) {
  return (
    <span className="thumbs" role="group" aria-label={`Rate: ${about}`}>
      <button
        type="button"
        className="icon"
        aria-pressed={rating === 1}
        aria-label="More like this"
        title="More like this (+)"
        onClick={() => {
          onRate(1);
        }}
      >
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <path d="M7 11v9H4a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1h3Zm0 0 4-8a2 2 0 0 1 2 2v4h5.5a2 2 0 0 1 2 2.3l-1.2 6.5a2 2 0 0 1-2 1.7H7" />
        </svg>
      </button>
      <button
        type="button"
        className="icon"
        aria-pressed={rating === -1}
        aria-label="Less like this"
        title="Less like this (-)"
        onClick={() => {
          onRate(-1);
        }}
      >
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" className="down">
          <path d="M7 11v9H4a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1h3Zm0 0 4-8a2 2 0 0 1 2 2v4h5.5a2 2 0 0 1 2 2.3l-1.2 6.5a2 2 0 0 1-2 1.7H7" />
        </svg>
      </button>
    </span>
  );
}

interface DoneProps {
  about: string;
  onDone: () => void;
}

/** Clears the item from the inbox; teaches nothing. */
export function DoneButton({ about, onDone }: DoneProps) {
  return (
    <button
      type="button"
      className="icon done"
      title="Done: remove from the inbox (e)"
      aria-label={`Done: ${about}`}
      onClick={onDone}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <path d="m5 12.5 4.5 4.5L19 7.5" />
      </svg>
      <span>Done</span>
    </button>
  );
}
