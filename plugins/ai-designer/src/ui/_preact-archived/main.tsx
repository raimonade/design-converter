import { render } from "preact";
import { App } from "./App";
import "./styles.css";

// Make functions available globally for onclick handlers
(window as any).figmaPostMessage = (message: any) => {
  parent.postMessage({ pluginMessage: message }, "*");
};

render(<App />, document.getElementById("app")!);
