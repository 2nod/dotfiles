const FLOW_PATH = "M 24 96 C 120 32 216 160 312 96";

export function FlowDiagram() {
  return (
    <svg className="flow-diagram" viewBox="0 0 336 192" role="img">
      <path className="flow-wire" d={FLOW_PATH} fill="none" />
      {[0, 1, 2].map((index) => (
        <circle key={index} className="flow-chip" r="6">
          <animateMotion
            dur="11s"
            begin={`${index * 0.44}s`}
            repeatCount="indefinite"
            path="M 24 96 C 120 32 216 160 312 96"
          />
        </circle>
      ))}
    </svg>
  );
}
