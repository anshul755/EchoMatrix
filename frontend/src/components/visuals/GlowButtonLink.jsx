import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Color, Mesh, Program, Renderer, Triangle } from 'ogl';

const vertex = /* glsl */ `
attribute vec2 uv;
attribute vec2 position;
varying vec2 vUv;

void main() {
  vUv = uv;
  gl_Position = vec4(position, 0.0, 1.0);
}
`;

const fragment = /* glsl */ `
precision highp float;

uniform float uTime;
uniform float uHover;
uniform vec2 uResolution;
uniform vec3 uGlow;

varying vec2 vUv;

float roundedBoxSDF(vec2 p, vec2 b, float r) {
  vec2 q = abs(p) - b + vec2(r);
  return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}

void main() {
  vec2 uv = vUv;
  vec2 p = uv - 0.5;
  float aspect = uResolution.x / max(uResolution.y, 1.0);
  p.x *= aspect;

  float outer = roundedBoxSDF(p, vec2(0.46 * aspect, 0.42), 0.16);
  float inner = roundedBoxSDF(p, vec2(0.43 * aspect, 0.37), 0.14);
  float border = smoothstep(0.03, -0.015, outer) - smoothstep(0.03, -0.015, inner);

  float sweep = 0.5 + 0.5 * sin(uTime * 1.7 + uv.x * 8.0 + uv.y * 4.0);
  float pulse = 0.35 + 0.65 * sweep;
  float alpha = border * (0.18 + uHover * 0.82) * pulse;

  vec3 color = uGlow * (0.75 + 0.45 * pulse);
  gl_FragColor = vec4(color, alpha);
}
`;

export default function GlowButtonLink({
  to,
  className = '',
  glow = '#8ddb44',
  children,
}) {
  const canvasHostRef = useRef(null);
  const hoverRef = useRef(false);
  const [hovered, setHovered] = useState(false);

  useEffect(() => {
    hoverRef.current = hovered;
  }, [hovered]);

  useEffect(() => {
    const container = canvasHostRef.current;
    if (!container) return undefined;

    const renderer = new Renderer({
      alpha: true,
      antialias: true,
      dpr: Math.min(window.devicePixelRatio || 1, 2),
    });

    const gl = renderer.gl;
    gl.clearColor(0, 0, 0, 0);
    container.appendChild(gl.canvas);

    const geometry = new Triangle(gl);
    const program = new Program(gl, {
      vertex,
      fragment,
      uniforms: {
        uTime: { value: 0 },
        uHover: { value: 0 },
        uResolution: { value: [1, 1] },
        uGlow: { value: new Color(glow) },
      },
      transparent: true,
    });

    const mesh = new Mesh(gl, { geometry, program });

    const resize = () => {
      const width = container.clientWidth || 1;
      const height = container.clientHeight || 1;
      renderer.setSize(width, height);
      program.uniforms.uResolution.value = [width, height];
    };

    resize();
    window.addEventListener('resize', resize);

    let frameId = 0;
    const start = performance.now();
    const tick = (time) => {
      const target = hoverRef.current ? 1 : 0;
      program.uniforms.uHover.value += (target - program.uniforms.uHover.value) * 0.08;
      program.uniforms.uTime.value = (time - start) * 0.001;
      renderer.render({ scene: mesh });
      frameId = requestAnimationFrame(tick);
    };
    frameId = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener('resize', resize);
      if (gl.canvas.parentNode === container) {
        container.removeChild(gl.canvas);
      }
      gl.getExtension('WEBGL_lose_context')?.loseContext();
    };
  }, [glow]);

  return (
    <Link
      to={to}
      className={`glow-link-button${className ? ` ${className}` : ''}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <span ref={canvasHostRef} className="glow-link-canvas" />
      <span className="glow-link-content">{children}</span>
    </Link>
  );
}
