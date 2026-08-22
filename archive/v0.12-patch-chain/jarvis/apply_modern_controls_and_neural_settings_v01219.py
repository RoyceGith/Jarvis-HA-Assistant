from pathlib import Path


ROOT = Path("/opt/jarvis")
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.19 patch missing: {label}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    require(text, old, label)
    return text.replace(old, new, 1)


def patch_backend(backend: str) -> str:
    defaults_marker = '    "theme": "dark",\n    "reduced_motion": False,'
    backend = replace_once(
        backend,
        defaults_marker,
        '    "theme": "dark",\n'
        '    "neural_style": "constellation",\n'
        '    "neural_scale": 1.0,\n'
        '    "neural_node_size": 1.0,\n'
        '    "neural_opacity": 0.38,\n'
        '    "reduced_motion": False,',
        "neural preference defaults",
    )

    model_marker = '    theme: str = Field(default="dark", pattern="^(dark|light|gray)$")\n    reduced_motion: bool = False'
    backend = replace_once(
        backend,
        model_marker,
        '    theme: str = Field(default="dark", pattern="^(dark|light|gray)$")\n'
        '    neural_style: str = Field(default="constellation", pattern="^(constellation|mesh|orbital|minimal)$")\n'
        '    neural_scale: float = Field(default=1.0, ge=0.7, le=1.4)\n'
        '    neural_node_size: float = Field(default=1.0, ge=0.6, le=1.6)\n'
        '    neural_opacity: float = Field(default=0.38, ge=0.05, le=0.8)\n'
        '    reduced_motion: bool = False',
        "settings validation",
    )

    save_marker = '                "theme": request.theme,\n                "reduced_motion": request.reduced_motion,'
    backend = replace_once(
        backend,
        save_marker,
        '                "theme": request.theme,\n'
        '                "neural_style": request.neural_style,\n'
        '                "neural_scale": request.neural_scale,\n'
        '                "neural_node_size": request.neural_node_size,\n'
        '                "neural_opacity": request.neural_opacity,\n'
        '                "reduced_motion": request.reduced_motion,',
        "preference persistence",
    )

    backend = backend.replace('version="0.12.18"', 'version="0.12.19"')
    backend = backend.replace('"version": "0.12.18"', '"version": "0.12.19"')
    return backend


def patch_frontend(frontend: str) -> str:
    style_close = frontend.find("</style>")
    if style_close < 0:
        raise RuntimeError("ZBRANO v0.12.19 patch missing: style close")
    css = r'''
    /* v0.12.19 modern neutral controls. Chat message colors intentionally remain unchanged. */
    :root { --neural-opacity: .38; }
    button {
      position: relative;
      border: 1px solid color-mix(in srgb, var(--line) 76%, #8aa1b8 24%);
      border-radius: 9px;
      background: linear-gradient(180deg, rgba(43, 52, 63, .78), rgba(22, 28, 35, .86));
      color: inherit;
      box-shadow: inset 0 1px rgba(255,255,255,.07), 0 5px 16px rgba(0,0,0,.16);
      transition: transform .16s ease, border-color .16s ease, background .16s ease, box-shadow .16s ease, color .16s ease;
    }
    button:hover:not(:disabled) {
      transform: translateY(-1px);
      border-color: color-mix(in srgb, var(--cyan) 62%, #91a7b9 38%);
      background: linear-gradient(180deg, rgba(52, 63, 76, .9), rgba(25, 33, 42, .94));
      color: var(--cyan);
      box-shadow: inset 0 1px rgba(255,255,255,.1), 0 8px 22px rgba(0,0,0,.22);
    }
    button:active:not(:disabled) { transform: translateY(0); box-shadow: inset 0 2px 8px rgba(0,0,0,.2); }
    button:focus-visible { outline: 2px solid color-mix(in srgb, var(--cyan) 72%, white 28%); outline-offset: 2px; }
    button.active {
      border-color: color-mix(in srgb, var(--cyan) 68%, #91a7b9 32%);
      background: linear-gradient(180deg, rgba(35, 70, 82, .88), rgba(19, 43, 52, .94));
      color: var(--cyan);
      box-shadow: inset 0 1px rgba(255,255,255,.08), 0 6px 18px rgba(0,0,0,.2);
    }
    :root[data-theme="light"] button {
      border-color: rgba(83, 102, 117, .28);
      background: linear-gradient(180deg, rgba(255,255,255,.98), rgba(237,241,245,.96));
      color: #26343f;
      box-shadow: inset 0 1px white, 0 5px 15px rgba(38,51,61,.11);
    }
    :root[data-theme="light"] button:hover:not(:disabled),
    :root[data-theme="light"] button.active {
      border-color: rgba(0,109,130,.48);
      background: linear-gradient(180deg, #fff, #e7f1f3);
      color: var(--cyan);
      box-shadow: 0 7px 18px rgba(38,51,61,.14);
    }
    .danger-action, #stop-button { color: #ffb4ad; }
    #mic-button { color: var(--cyan); }
    #brain-network { opacity: var(--neural-opacity) !important; }
    .core-stage.neuron-intense #brain-network { opacity: calc(var(--neural-opacity) * 1.9) !important; }
    body.jarvis-input-active #brain-network { opacity: calc(var(--neural-opacity) * .1) !important; }
    .neural-controls { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--line); }
    .neural-controls h3 { margin: 0 0 .3rem; color: var(--cyan); font-size: .88rem; font-weight: 600; letter-spacing: .05em; }
    .neural-control-grid { display: grid; grid-template-columns: repeat(2, minmax(220px, 1fr)); gap: .9rem 1.1rem; margin-top: .75rem; }
    .neural-range { display: grid; grid-template-columns: 1fr 4rem; gap: .35rem .7rem; align-items: center; }
    .neural-range label { font-weight: 650; }
    .neural-range output { color: var(--cyan); text-align: right; font-variant-numeric: tabular-nums; }
    .neural-range input { grid-column: 1 / -1; width: 100%; accent-color: var(--cyan); }
    @media (max-width: 760px) { .neural-control-grid { grid-template-columns: 1fr; } }
'''
    frontend = frontend[:style_close] + css + frontend[style_close:]

    controls_marker = '        <label class="toggle-row"><input id="reduced-motion" type="checkbox"> Reduce neural motion and animations</label>'
    controls = r'''        <label class="toggle-row"><input id="reduced-motion" type="checkbox"> Reduce neural motion and animations</label>
      </div>
      <div class="neural-controls">
        <h3>NEURAL BACKGROUND</h3>
        <small class="setting-note">Personalize the neural visualization behind chat. These controls do not change chat text colors.</small>
        <div class="neural-control-grid">
          <div class="setting-field">
            <label for="neural-style">Design style</label>
            <select id="neural-style">
              <option value="constellation">Constellation</option>
              <option value="mesh">Neural mesh</option>
              <option value="orbital">Orbital core</option>
              <option value="minimal">Minimal</option>
            </select>
          </div>
          <div class="neural-range">
            <label for="neural-scale">Network size</label><output id="neural-scale-value">100%</output>
            <input id="neural-scale" type="range" min="0.7" max="1.4" step="0.05" value="1">
          </div>
          <div class="neural-range">
            <label for="neural-node-size">Node size</label><output id="neural-node-size-value">100%</output>
            <input id="neural-node-size" type="range" min="0.6" max="1.6" step="0.05" value="1">
          </div>
          <div class="neural-range">
            <label for="neural-opacity">Chat opacity</label><output id="neural-opacity-value">38%</output>
            <input id="neural-opacity" type="range" min="0.05" max="0.8" step="0.01" value="0.38">
          </div>
        </div>'''
    frontend = replace_once(frontend, controls_marker, controls, "neural settings controls")

    const_marker = 'const reducedMotionSetting = document.getElementById("reduced-motion");'
    frontend = replace_once(
        frontend,
        const_marker,
        const_marker + r'''
const neuralStyle = document.getElementById("neural-style");
const neuralScale = document.getElementById("neural-scale");
const neuralNodeSize = document.getElementById("neural-node-size");
const neuralOpacity = document.getElementById("neural-opacity");
const neuralScaleValue = document.getElementById("neural-scale-value");
const neuralNodeSizeValue = document.getElementById("neural-node-size-value");
const neuralOpacityValue = document.getElementById("neural-opacity-value");''',
        "neural control bindings",
    )

    apply_marker = '  document.documentElement.dataset.reducedMotion = String(Boolean(preferences.reduced_motion));'
    frontend = replace_once(
        frontend,
        apply_marker,
        r'''  const style = ["constellation", "mesh", "orbital", "minimal"].includes(preferences.neural_style)
    ? preferences.neural_style : "constellation";
  const scale = Math.min(1.4, Math.max(.7, Number(preferences.neural_scale) || 1));
  const nodeSize = Math.min(1.6, Math.max(.6, Number(preferences.neural_node_size) || 1));
  const opacity = Math.min(.8, Math.max(.05, Number(preferences.neural_opacity) || .38));
  document.documentElement.dataset.neuralStyle = style;
  document.documentElement.dataset.neuralScale = String(scale);
  document.documentElement.dataset.neuralNodeSize = String(nodeSize);
  document.documentElement.style.setProperty("--neural-opacity", String(opacity));
  if (neuralStyle) neuralStyle.value = style;
  if (neuralScale) neuralScale.value = String(scale);
  if (neuralNodeSize) neuralNodeSize.value = String(nodeSize);
  if (neuralOpacity) neuralOpacity.value = String(opacity);
  if (neuralScaleValue) neuralScaleValue.textContent = `${Math.round(scale * 100)}%`;
  if (neuralNodeSizeValue) neuralNodeSizeValue.textContent = `${Math.round(nodeSize * 100)}%`;
  if (neuralOpacityValue) neuralOpacityValue.textContent = `${Math.round(opacity * 100)}%`;
  document.documentElement.dataset.reducedMotion = String(Boolean(preferences.reduced_motion));
  window.dispatchEvent(new CustomEvent("zbrano-neural-change"));''',
        "preference application",
    )

    listener_marker = 'voiceVolume.addEventListener("input", () => {'
    listeners = r'''for (const [control, output] of [
  [neuralScale, neuralScaleValue],
  [neuralNodeSize, neuralNodeSizeValue],
  [neuralOpacity, neuralOpacityValue],
]) {
  control.addEventListener("input", () => {
    output.textContent = `${Math.round(Number(control.value) * 100)}%`;
    applyInterfacePreferences({
      ...jarvisPreferences,
      neural_style: neuralStyle.value,
      neural_scale: Number(neuralScale.value),
      neural_node_size: Number(neuralNodeSize.value),
      neural_opacity: Number(neuralOpacity.value),
    });
  });
}
neuralStyle.addEventListener("change", () => applyInterfacePreferences({
  ...jarvisPreferences,
  neural_style: neuralStyle.value,
  neural_scale: Number(neuralScale.value),
  neural_node_size: Number(neuralNodeSize.value),
  neural_opacity: Number(neuralOpacity.value),
}));

'''
    frontend = replace_once(frontend, listener_marker, listeners + listener_marker, "live neural preview")

    load_marker = '    reducedMotionSetting.checked = Boolean(jarvisPreferences.reduced_motion);'
    frontend = replace_once(
        frontend,
        load_marker,
        '    neuralStyle.value = jarvisPreferences.neural_style || "constellation";\n'
        '    neuralScale.value = String(jarvisPreferences.neural_scale ?? 1);\n'
        '    neuralNodeSize.value = String(jarvisPreferences.neural_node_size ?? 1);\n'
        '    neuralOpacity.value = String(jarvisPreferences.neural_opacity ?? .38);\n'
        + load_marker,
        "settings load",
    )

    save_marker = '        theme: document.querySelector(\'input[name="theme"]:checked\')?.value || "dark",\n        reduced_motion: reducedMotionSetting.checked,'
    frontend = replace_once(
        frontend,
        save_marker,
        '        theme: document.querySelector(\'input[name="theme"]:checked\')?.value || "dark",\n'
        '        neural_style: neuralStyle.value,\n'
        '        neural_scale: Number(neuralScale.value),\n'
        '        neural_node_size: Number(neuralNodeSize.value),\n'
        '        neural_opacity: Number(neuralOpacity.value),\n'
        '        reduced_motion: reducedMotionSetting.checked,',
        "settings save payload",
    )

    radius_marker = '    const sphereRadius = Math.min(width * .41, height * .39, 300);'
    frontend = replace_once(
        frontend,
        radius_marker,
        r'''    const neuralStyleName = document.documentElement.dataset.neuralStyle || "constellation";
    const neuralScaleFactor = Number(document.documentElement.dataset.neuralScale) || 1;
    const neuralNodeScale = Number(document.documentElement.dataset.neuralNodeSize) || 1;
    const sphereRadius = Math.min(width * .41, height * .39, 300) * neuralScaleFactor;''',
        "network scaling",
    )

    projection_marker = '        y: centerY + rotatedY * sphereRadius * perspective,'
    frontend = replace_once(
        frontend,
        projection_marker,
        '        y: centerY + rotatedY * sphereRadius * perspective * (neuralStyleName === "orbital" ? .48 : 1),',
        "orbital projection",
    )

    link_loop = '    for (const link of links) {\n      const from = projected[link.from];'
    frontend = replace_once(
        frontend,
        link_loop,
        '    for (const [linkIndex, link] of links.entries()) {\n'
        '      if (neuralStyleName === "minimal" && linkIndex % 5 !== 0) continue;\n'
        '      if (neuralStyleName === "orbital" && linkIndex % 2 !== 0) continue;\n'
        '      const from = projected[link.from];',
        "style-specific links",
    )

    line_width_marker = '      context.lineWidth = .85 + Math.max(0, (from.z + to.z) * .12);'
    frontend = replace_once(
        frontend,
        line_width_marker,
        '      context.lineWidth = (.85 + Math.max(0, (from.z + to.z) * .12)) * (neuralStyleName === "mesh" ? 1.7 : neuralStyleName === "minimal" ? .65 : 1);',
        "mesh link treatment",
    )

    node_loop = '    for (const point of projected) {\n      const pulse = reducedMotion ? 1 : .82 + Math.sin(now * .0012 + point.node.phase) * .18;'
    frontend = replace_once(
        frontend,
        node_loop,
        '    for (const [pointIndex, point] of projected.entries()) {\n'
        '      if (neuralStyleName === "minimal" && pointIndex % 3 !== 0) continue;\n'
        '      const pulse = reducedMotion ? 1 : .82 + Math.sin(now * .0012 + point.node.phase) * .18;',
        "minimal node treatment",
    )
    node_radius_marker = '      const nodeRadius = Math.max(1, (1.35 + point.node.weight * 1.05) * point.perspective * pulse);'
    frontend = replace_once(
        frontend,
        node_radius_marker,
        '      const styleNodeScale = neuralStyleName === "mesh" ? .72 : neuralStyleName === "orbital" ? 1.18 : 1;\n'
        '      const nodeRadius = Math.max(.65, (1.35 + point.node.weight * 1.05) * point.perspective * pulse * neuralNodeScale * styleNodeScale);',
        "node scaling",
    )

    theme_listener = '  window.addEventListener("jarvis-theme-change", () => {\n    if (frame) window.cancelAnimationFrame(frame);\n    draw(performance.now(), true);\n  });'
    frontend = replace_once(
        frontend,
        theme_listener,
        theme_listener + r'''
  window.addEventListener("zbrano-neural-change", () => {
    if (frame) window.cancelAnimationFrame(frame);
    draw(performance.now(), true);
  });''',
        "neural live redraw",
    )

    frontend = frontend.replace("HUD 0.12.18", "HUD 0.12.19")
    return frontend


def verify() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")
    for marker in (
        'version="0.12.19"',
        '"neural_style": "constellation"',
        "neural_opacity: float",
        '"neural_node_size": request.neural_node_size',
    ):
        require(backend, marker, marker)
    for marker in (
        "HUD 0.12.19",
        'id="neural-style"',
        'id="neural-scale"',
        'id="neural-node-size"',
        'id="neural-opacity"',
        'dataset.neuralStyle',
        'CustomEvent("zbrano-neural-change")',
        "modern neutral controls",
        "neuralStyleName === \"orbital\"",
        "neuralStyleName === \"minimal\"",
    ):
        require(frontend, marker, marker)


def main() -> None:
    backend = patch_backend(MAIN.read_text(encoding="utf-8"))
    frontend = patch_frontend(INDEX.read_text(encoding="utf-8"))
    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")
    verify()


if __name__ == "__main__":
    main()
