import { executeTool, executeBatch, resetContext, getContext, type ToolResult } from './tool-executor';

export interface PhasePlan {
  phase: number;
  name: string;
  description: string;
  operations: Array<{ tool: string; args: Record<string, unknown> }>;
}

export interface ExecutionResult {
  success: boolean;
  phases: PhaseResult[];
  summary: string;
  errors: string[];
}

export interface PhaseResult {
  phase: number;
  name: string;
  success: boolean;
  results: ToolResult[];
  errors: string[];
}

export async function executePhase(plan: PhasePlan): Promise<PhaseResult> {
  console.log(`Executing Phase ${plan.phase}: ${plan.name}`);
  
  const results: ToolResult[] = [];
  const errors: string[] = [];
  
  try {
    for (const op of plan.operations) {
      const result = await executeTool(op.tool, op.args);
      results.push(result);
      
      if (!result.success && result.error) {
        errors.push(`${op.tool}: ${result.error}`);
        console.log(`Tool error: ${op.tool} - ${result.error}`);
      }
    }
    
    return {
      phase: plan.phase,
      name: plan.name,
      success: errors.length === 0,
      results,
      errors
    };
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : 'Unknown error';
    errors.push(`Phase ${plan.phase} failed: ${errorMsg}`);
    
    return {
      phase: plan.phase,
      name: plan.name,
      success: false,
      results,
      errors
    };
  }
}

export async function executeAllPhases(plans: PhasePlan[]): Promise<ExecutionResult> {
  resetContext();
  
  const phaseResults: PhaseResult[] = [];
  const allErrors: string[] = [];
  
  for (const plan of plans) {
    const result = await executePhase(plan);
    phaseResults.push(result);
    allErrors.push(...result.errors);
    
    if (!result.success) {
      console.log(`Phase ${plan.phase} had errors, continuing...`);
    }
  }
  
  const context = getContext();
  
  return {
    success: allErrors.length === 0,
    phases: phaseResults,
    summary: `Created ${context.created.length} elements. Errors: ${allErrors.length}`,
    errors: allErrors
  };
}

export function parsePhasePlansFromResponse(aiResponse: string): PhasePlan[] {
  const plans: PhasePlan[] = [];
  
  try {
    const jsonMatch = aiResponse.match(/\[[\s\S]*\]/);
    if (!jsonMatch) {
      console.log('No phase plans found in response');
      return plans;
    }
    
    const parsed = JSON.parse(jsonMatch[0]);
    
    for (const p of parsed) {
      plans.push({
        phase: p.phase || plans.length + 1,
        name: p.name || `Phase ${plans.length + 1}`,
        description: p.description || '',
        operations: p.operations || []
      });
    }
  } catch (e) {
    console.log('Failed to parse phase plans:', e);
  }
  
  return plans;
}

export { executeTool, executeBatch, getContext, resetContext };
