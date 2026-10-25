/** A source's mark: its initials on a pale tint of a hue taken from its name, so the same source always looks the same. */
const HUES = [8, 28, 46, 95, 150, 175, 195, 215, 330, 350];

export const markOf = (name: string): { initials: string; hue: number } => {
  const words = name.split(/[^A-Za-z0-9]+/).filter(Boolean);
  const first = words[0] ?? "?";
  const initials = words.length > 1 ? first.charAt(0) + (words[1] as string).charAt(0) : first.slice(0, 2);
  let sum = 0;
  for (let i = 0; i < name.length; i += 1) sum += name.charCodeAt(i);
  return {
    initials: initials.charAt(0).toUpperCase() + initials.slice(1).toLowerCase(),
    hue: HUES[sum % HUES.length] as number,
  };
};

export function SourceMark({ name }: { name: string }) {
  const { initials, hue } = markOf(name);
  return (
    <span className="mark" style={{ "--hue": hue } as React.CSSProperties} aria-hidden="true">
      {initials}
    </span>
  );
}
