import { useEffect, useRef } from "react";

export function useMathJaxTypeset(deps) {
  const ref = useRef(null);

  useEffect(() => {
    if (window.MathJax?.typesetPromise && ref.current) {
      window.MathJax.typesetPromise([ref.current]).catch((err) =>
        console.error("MathJax typeset failed", err)
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return ref;
}
