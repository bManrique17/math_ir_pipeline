import { useMathJaxTypeset } from "../hooks/useMathJax";

export default function PostText({ content }) {
  const ref = useMathJaxTypeset([content]);

  if (!content || content.length === 0) {
    return <p className="text-muted fst-italic">(no text)</p>;
  }

  return (
    <div ref={ref} className="post-text">
      {content.map((seg, i) =>
        seg.type === "formula" ? (
          <span key={i} className="mx-1">{`\\(${seg.latex}\\)`}</span>
        ) : (
          <span key={i}>{seg.text}</span>
        )
      )}
    </div>
  );
}
