/**
 * Design System Builder - Executed by AI via figma-console-mcp
 * 
 * Creates:
 * - Variable collection "Design System V1" with Light/Dark modes
 * - Primitives: slate colors, blue-500/600/700, white, spacing, radius
 * - Semantics: aliases pointing to primitives
 * - Components: Button, Input with variable bindings
 * - Frames: organized with auto-layout
 */

async function buildDesignSystem() {
  console.log('Building Design System...');

  const collection = figma.variables.createVariableCollection('Design System V1');
  const lightModeId = collection.modes[0]?.modeId;
  const darkModeId = collection.modes[1]?.modeId || collection.addMode('Dark');

  const primitives = {};
  const semantics = {};

  async function createColorPrimitive(name, lightColor, darkColor) {
    const variable = figma.variables.createVariable(name, collection, 'COLOR');
    variable.setValueForMode(lightModeId, lightColor);
    variable.setValueForMode(darkModeId, darkColor);
    primitives[name] = variable;
    return variable;
  }

  async function createNumberPrimitive(name, value) {
    const variable = figma.variables.createVariable(name, collection, 'FLOAT');
    variable.setValueForMode(lightModeId, value);
    variable.setValueForMode(darkModeId, value);
    primitives[name] = variable;
    return variable;
  }

  async function createSemanticAlias(name, primitivePath) {
    const primitive = primitives[primitivePath];
    if (!primitive) {
      console.error('Primitive not found:', primitivePath);
      return null;
    }
    const variable = figma.variables.createVariable(name, collection, 'COLOR');
    const alias = figma.variables.createVariableAlias(primitive);
    variable.setValueForMode(lightModeId, alias);
    variable.setValueForMode(darkModeId, alias);
    semantics[name] = variable;
    return variable;
  }

  await createColorPrimitive('primitive/colors/slate-50', { r: 0.98, g: 0.98, b: 0.98 }, { r: 0.09, g: 0.09, b: 0.09 });
  await createColorPrimitive('primitive/colors/slate-100', { r: 0.96, g: 0.96, b: 0.96 }, { r: 0.15, g: 0.15, b: 0.15 });
  await createColorPrimitive('primitive/colors/slate-200', { r: 0.90, g: 0.90, b: 0.91 }, { r: 0.25, g: 0.25, b: 0.27 });
  await createColorPrimitive('primitive/colors/slate-300', { r: 0.83, g: 0.83, b: 0.85 }, { r: 0.32, g: 0.32, b: 0.36 });
  await createColorPrimitive('primitive/colors/slate-400', { r: 0.63, g: 0.63, b: 0.67 }, { r: 0.44, g: 0.44, b: 0.48 });
  await createColorPrimitive('primitive/colors/slate-500', { r: 0.44, g: 0.44, b: 0.48 }, { r: 0.44, g: 0.44, b: 0.48 });
  await createColorPrimitive('primitive/colors/slate-600', { r: 0.32, g: 0.32, b: 0.36 }, { r: 0.63, g: 0.63, b: 0.67 });
  await createColorPrimitive('primitive/colors/slate-700', { r: 0.25, g: 0.25, b: 0.27 }, { r: 0.83, g: 0.83, b: 0.85 });
  await createColorPrimitive('primitive/colors/slate-800', { r: 0.15, g: 0.15, b: 0.16 }, { r: 0.90, g: 0.90, b: 0.91 });
  await createColorPrimitive('primitive/colors/slate-900', { r: 0.09, g: 0.09, b: 0.11 }, { r: 0.96, g: 0.96, b: 0.96 });
  await createColorPrimitive('primitive/colors/blue-500', { r: 0.30, g: 0.49, b: 1.0 }, { r: 0.30, g: 0.49, b: 1.0 });
  await createColorPrimitive('primitive/colors/blue-600', { r: 0.23, g: 0.38, b: 1.0 }, { r: 0.23, g: 0.38, b: 1.0 });
  await createColorPrimitive('primitive/colors/white', { r: 1.0, g: 1.0, b: 1.0 }, { r: 1.0, g: 1.0, b: 1.0 });

  await createNumberPrimitive('primitive/spacing/1', 4);
  await createNumberPrimitive('primitive/spacing/2', 8);
  await createNumberPrimitive('primitive/spacing/3', 12);
  await createNumberPrimitive('primitive/spacing/4', 16);
  await createNumberPrimitive('primitive/spacing/6', 24);
  await createNumberPrimitive('primitive/spacing/8', 32);

  await createNumberPrimitive('primitive/radius/sm', 4);
  await createNumberPrimitive('primitive/radius/md', 8);
  await createNumberPrimitive('primitive/radius/lg', 12);

  console.log('Created', Object.keys(primitives).length, 'primitives');

  await createSemanticAlias('semantic/colors/background', 'primitive/colors/slate-50');
  await createSemanticAlias('semantic/colors/foreground', 'primitive/colors/slate-900');
  await createSemanticAlias('semantic/colors/foreground-secondary', 'primitive/colors/slate-600');
  await createSemanticAlias('semantic/colors/primary', 'primitive/colors/blue-500');
  await createSemanticAlias('semantic/colors/primary-hover', 'primitive/colors/blue-600');
  await createSemanticAlias('semantic/colors/primary-foreground', 'primitive/colors/white');
  await createSemanticAlias('semantic/colors/border', 'primitive/colors/slate-200');

  console.log('Created', Object.keys(semantics).length, 'semantic aliases');

  const page = figma.createPage();
  page.name = 'Design System V1';

  const atomsFrame = figma.createFrame();
  atomsFrame.name = 'Atoms';
  atomsFrame.layoutMode = 'VERTICAL';
  atomsFrame.primaryAxisSizingMode = 'AUTO';
  atomsFrame.counterAxisSizingMode = 'FIXED';
  atomsFrame.resize(400, 1);
  atomsFrame.itemSpacing = 24;
  atomsFrame.paddingLeft = 24;
  atomsFrame.paddingRight = 24;
  atomsFrame.paddingTop = 24;
  atomsFrame.paddingBottom = 24;
  atomsFrame.fills = [{ type: 'SOLID', color: { r: 0.98, g: 0.98, b: 0.98 } }];
  page.appendChild(atomsFrame);

  await figma.loadFontAsync({ family: 'Inter', style: 'Semi Bold' });
  await figma.loadFontAsync({ family: 'Inter', style: 'Regular' });

  const button = figma.createComponent();
  button.name = 'Button/Primary';
  button.layoutMode = 'HORIZONTAL';
  button.primaryAxisSizingMode = 'AUTO';
  button.counterAxisSizingMode = 'AUTO';
  button.itemSpacing = 8;
  button.paddingLeft = 16;
  button.paddingRight = 16;
  button.paddingTop = 10;
  button.paddingBottom = 10;
  button.cornerRadius = 8;

  const buttonText = figma.createText();
  buttonText.characters = 'Button';
  buttonText.fontFamily = 'Inter';
  buttonText.fontWeight = 600;
  buttonText.fontSize = 14;
  button.appendChild(buttonText);

  const primaryVar = semantics['semantic/colors/primary'];
  const primaryFgVar = semantics['semantic/colors/primary-foreground'];

  if (primaryVar && primaryFgVar) {
    const bgFill = { type: 'SOLID', color: { r: 0, g: 0, b: 0 }, boundVariables: {} };
    const boundBgFill = figma.variables.setBoundVariableForPaint(bgFill, 'color', primaryVar);
    button.fills = [boundBgFill];

    const textFill = { type: 'SOLID', color: { r: 0, g: 0, b: 0 }, boundVariables: {} };
    const boundTextFill = figma.variables.setBoundVariableForPaint(textFill, 'color', primaryFgVar);
    buttonText.fills = [boundTextFill];

    console.log('Button bound to semantic variables');
  }

  atomsFrame.appendChild(button);

  const input = figma.createComponent();
  input.name = 'Input/Default';
  input.layoutMode = 'HORIZONTAL';
  input.primaryAxisSizingMode = 'AUTO';
  input.counterAxisSizingMode = 'FIXED';
  input.resize(200, 40);
  input.paddingLeft = 12;
  input.paddingRight = 12;
  input.paddingTop = 10;
  input.paddingBottom = 10;
  input.cornerRadius = 6;

  const inputText = figma.createText();
  inputText.characters = 'Placeholder...';
  inputText.fontFamily = 'Inter';
  inputText.fontWeight = 400;
  inputText.fontSize = 14;
  input.appendChild(inputText);

  const borderVar = semantics['semantic/colors/border'];
  const bgVar = semantics['semantic/colors/background'];

  if (borderVar && bgVar) {
    const borderPaint = { type: 'SOLID', color: { r: 0, g: 0, b: 0 }, boundVariables: {} };
    const boundBorder = figma.variables.setBoundVariableForPaint(borderPaint, 'color', borderVar);
    input.strokes = [boundBorder];
    input.strokeWeight = 1;

    const bgPaint = { type: 'SOLID', color: { r: 0, g: 0, b: 0 }, boundVariables: {} };
    const boundBg = figma.variables.setBoundVariableForPaint(bgPaint, 'color', bgVar);
    input.fills = [boundBg];

    console.log('Input bound to semantic variables');
  }

  atomsFrame.appendChild(input);

  console.log('Design System built successfully!');
  figma.notify('Design System V1 created with ' + Object.keys(primitives).length + ' primitives, ' + Object.keys(semantics).length + ' semantics');

  return {
    primitives: Object.keys(primitives).length,
    semantics: Object.keys(semantics).length,
    components: ['Button/Primary', 'Input/Default']
  };
}

buildDesignSystem();
