# 🧠 How Claude-Flow Works: Complete Architecture Guide

## 📋 Table of Contents

1. [Overview](#overview)
2. [Core Concepts](#core-concepts)
3. [Architecture](#architecture)
4. [Execution Flow](#execution-flow)
5. [Integration with Claude Code](#integration-with-claude-code)
6. [Practical Examples](#practical-examples)
7. [Under the Hood](#under-the-hood)

---

## Overview

Claude-Flow is an **AI orchestration platform** that enables multiple AI agents to work together on complex development tasks. Think of it as a "project manager + team of specialists" for AI-powered development.

### The Big Picture

```
┌─────────────────────────────────────────────────────────────┐
│                      YOU (User)                              │
│                         ↓                                    │
│            Claude Code (with MCP Tools)                      │
│                         ↓                                    │
│         ┌───────────────────────────────┐                   │
│         │     Claude-Flow Platform      │                   │
│         ├───────────────────────────────┤                   │
│         │ • 25 Skills (Auto-activate)   │                   │
│         │ • 64 Specialized Agents       │                   │
│         │ • 100+ MCP Tools              │                   │
│         │ • Persistent Memory (SQLite)  │                   │
│         │ • Swarm Orchestration         │                   │
│         └───────────────────────────────┘                   │
│                         ↓                                    │
│         Multiple AI Agents Working in Parallel              │
│         (Coder, Tester, Reviewer, Researcher, etc.)         │
│                         ↓                                    │
│              Your Project Gets Built                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Concepts

### 1. **Skills** (25 Total)

Skills are **natural language-activated capabilities** that Claude Code automatically detects and uses.

**How They Work:**
- You describe what you want in natural language
- Claude Code detects the intent
- The appropriate skill activates automatically
- No commands to memorize!

**Example:**
```
You say: "Let's pair program on this feature"
→ Claude detects: pair-programming skill needed
→ Activates: pair-programming skill
→ Result: Interactive coding session with AI driver/navigator roles
```

**Skill Categories:**
- **Development**: Pair programming, SPARC methodology, skill builder
- **Intelligence**: Vector search, memory patterns, learning
- **Swarm**: Multi-agent orchestration, advanced coordination
- **GitHub**: Code review, release management, multi-repo
- **Automation**: Hooks, verification, performance analysis
- **Platform**: Cloud features, neural training, sandboxes

### 2. **Agents** (64 Total)

Agents are **specialized AI workers** that perform specific development tasks.

**How They Work:**
- Each agent has a specific role (coder, tester, reviewer, etc.)
- Agents have instructions, capabilities, and hooks
- Multiple agents can work in parallel (swarm)
- Agents coordinate through shared memory

**Agent Structure:**
```yaml
name: coder
type: developer
description: Implementation specialist
capabilities:
  - code_generation
  - refactoring
  - optimization
hooks:
  pre: "Setup before coding"
  post: "Validate after coding"
```

**Key Agent Types:**
- **Core**: coder, tester, reviewer, researcher, planner
- **Specialized**: backend-dev, mobile-dev, ml-developer
- **GitHub**: pr-manager, issue-tracker, release-manager
- **Swarm**: hierarchical-coordinator, mesh-coordinator
- **Consensus**: byzantine-coordinator, raft-manager
- **Performance**: perf-analyzer, load-balancer

### 3. **Swarms**

A swarm is **multiple agents working together** on a complex task.

**How They Work:**
```
Task: "Build a REST API with authentication"

┌─────────────────────────────────────────────┐
│         Swarm Coordinator (Queen)           │
│    Breaks down task into sub-tasks          │
└─────────────────────────────────────────────┘
                  ↓
    ┌─────────────┬──────────────┬─────────────┐
    ↓             ↓              ↓             ↓
┌────────┐  ┌─────────┐  ┌────────┐  ┌─────────┐
│Researcher│  │Backend  │  │Tester  │  │Reviewer │
│Agent    │  │Agent    │  │Agent   │  │Agent    │
└────────┘  └─────────┘  └────────┘  └─────────┘
    │            │            │            │
    └────────────┴────────────┴────────────┘
                  ↓
          Shared Memory (SQLite)
    (All agents read/write progress)
```

**Topology Types:**
1. **Mesh** - All agents communicate peer-to-peer
2. **Hierarchical** - Queen coordinates workers
3. **Adaptive** - Automatically switches based on task

### 4. **Memory System** (ReasoningBank)

Persistent storage that **all agents share** to coordinate work.

**How It Works:**
```
Agent A: Stores decision
    ↓
SQLite Database (.swarm/memory.db)
    ↓
Agent B: Reads decision and builds on it
```

**Features:**
- **Persistent**: Survives restarts
- **Semantic Search**: Find by meaning (2-3ms latency)
- **Hash Embeddings**: Works without API keys
- **Namespace Isolation**: Organize by domain

**Example Flow:**
```bash
# Coder agent stores API schema
memory.store("api-schema", { endpoints: [...] })

# Tester agent retrieves it
schema = memory.retrieve("api-schema")

# Tester writes tests based on schema
```

### 5. **MCP Tools** (100+ Total)

MCP (Model Context Protocol) tools are **functions Claude can call** to perform actions.

**Categories:**
```javascript
// Swarm Orchestration
mcp__claude-flow__swarm_init({ topology: "mesh" })
mcp__claude-flow__agent_spawn({ type: "coder" })
mcp__claude-flow__task_orchestrate({ task: "Build API" })

// Memory Management
mcp__claude-flow__memory_usage({ action: "store" })
mcp__claude-flow__memory_search({ query: "API" })

// GitHub Integration
mcp__claude-flow__github_swarm({ mode: "pr-review" })
mcp__claude-flow__repo_analyze({ repo: "owner/repo" })

// Performance
mcp__claude-flow__benchmark_run({ suite: "api" })
mcp__claude-flow__bottleneck_analyze({ })
```

### 6. **Hooks System**

Hooks are **automatic actions** that run before/after operations.

**Hook Types:**
```
Pre-Operation Hooks:
├── pre-task: Assign agents, check memory
├── pre-edit: Validate files, prepare resources
└── pre-command: Security validation

Post-Operation Hooks:
├── post-edit: Auto-format, lint code
├── post-task: Train neural patterns, update memory
└── post-command: Save metrics, update stats

Session Hooks:
├── session-start: Restore context
├── session-end: Generate summary
└── session-restore: Load memory
```

---

## Architecture

### System Architecture

```
┌───────────────────────────────────────────────────────┐
│                    Claude Code                         │
│  (Your AI Assistant - What you interact with)         │
└───────────────────────────────────────────────────────┘
                         ↓
         MCP Protocol (Model Context Protocol)
                         ↓
┌───────────────────────────────────────────────────────┐
│              Claude-Flow MCP Server                    │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Skill Detection Engine                         │  │
│  │  • Analyzes user intent                         │  │
│  │  • Matches to skills                            │  │
│  │  • Activates appropriate handlers               │  │
│  └─────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Swarm Orchestration Layer                      │  │
│  │  • Task decomposition                           │  │
│  │  • Agent assignment                             │  │
│  │  • Topology management                          │  │
│  └─────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Agent Runtime                                   │  │
│  │  • 64 agent definitions                         │  │
│  │  • Parallel execution                           │  │
│  │  • Hook execution                               │  │
│  └─────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Memory System (ReasoningBank)                  │  │
│  │  • SQLite database                              │  │
│  │  • Semantic search                              │  │
│  │  • Cross-agent coordination                     │  │
│  └─────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────┘
```

### Data Flow

```
1. User Request
   ↓
2. Claude Code analyzes intent
   ↓
3. Calls appropriate MCP tool
   ↓
4. Claude-Flow receives MCP call
   ↓
5. Skill activated OR Swarm spawned
   ↓
6. Agents execute tasks in parallel
   ↓
7. Each agent:
   - Runs pre-hooks
   - Executes task
   - Stores results in memory
   - Runs post-hooks
   ↓
8. Swarm coordinator collects results
   ↓
9. Response sent back to Claude Code
   ↓
10. Claude Code shows you the results
```

---

## Execution Flow

### Example: Building a REST API

Let's trace how "Build a REST API with authentication" gets executed:

#### Step 1: User Request
```
You: "Build a REST API with authentication"
```

#### Step 2: Claude Code Analyzes
```javascript
Claude Code thinks:
- This is a complex task
- Needs multiple specialists
- Should use swarm orchestration skill
```

#### Step 3: Skill Activation
```javascript
// Claude Code calls MCP tool
mcp__claude-flow__swarm_init({
  topology: "adaptive",
  maxAgents: 5
})
```

#### Step 4: Task Decomposition
```
Swarm Coordinator breaks down task:
├── Research: Best practices for REST APIs
├── Design: API architecture and endpoints
├── Implement: Code the API endpoints
├── Secure: Add authentication (JWT)
├── Test: Write test suite
└── Review: Code quality check
```

#### Step 5: Agent Assignment
```
Researcher Agent → Research task
Backend-Dev Agent → Design + Implement
Security Agent → Secure task
Tester Agent → Test task
Reviewer Agent → Review task
```

#### Step 6: Parallel Execution

**Researcher Agent:**
```bash
# Pre-hook
npx claude-flow hooks pre-task --description "Research REST APIs"

# Main work
- Researches REST best practices
- Stores findings in memory

# Post-hook
npx claude-flow hooks post-task --update-memory
```

**Backend-Dev Agent:**
```typescript
// Reads researcher's findings from memory
const research = await memory.retrieve('api-research');

// Designs API
const apiDesign = {
  endpoints: [
    'POST /auth/login',
    'POST /auth/logout',
    'GET /users',
    'POST /users'
  ]
};

// Stores design in memory
await memory.store('api-design', apiDesign);

// Implements code
// (generates Express.js code)

// Stores implementation status
await memory.store('api-implementation', {
  status: 'complete',
  files: ['server.js', 'routes/auth.js', 'routes/users.js']
});
```

**Tester Agent:**
```typescript
// Waits for implementation
while (await memory.retrieve('api-implementation').status !== 'complete') {
  await sleep(1000);
}

// Reads API design
const design = await memory.retrieve('api-design');

// Generates tests
const tests = generateTests(design);

// Stores test results
await memory.store('test-results', {
  coverage: '95%',
  passing: true
});
```

**Reviewer Agent:**
```typescript
// Waits for tests
const testResults = await memory.retrieve('test-results');

// Reviews code
const review = {
  security: 'Pass',
  performance: 'Good',
  style: 'Consistent',
  issues: []
};

// Stores review
await memory.store('code-review', review);
```

#### Step 7: Coordination

All agents communicate through memory:
```
Memory Database (.swarm/memory.db):
├── api-research: { bestPractices: [...] }
├── api-design: { endpoints: [...] }
├── api-implementation: { status: 'complete', files: [...] }
├── test-results: { coverage: '95%', passing: true }
└── code-review: { security: 'Pass', ... }
```

#### Step 8: Result Assembly

Swarm coordinator:
1. Checks all agents completed
2. Reads final results from memory
3. Assembles complete response

#### Step 9: Response to User

```
✅ REST API with authentication built successfully!

Files created:
- server.js (Express server)
- routes/auth.js (Login/logout)
- routes/users.js (User CRUD)
- middleware/auth.js (JWT verification)
- tests/api.test.js (95% coverage)

Features:
✓ JWT authentication
✓ Password hashing (bcrypt)
✓ Rate limiting
✓ Input validation
✓ Error handling
✓ Comprehensive tests

Next steps:
1. Review the code
2. Run tests: npm test
3. Start server: npm start
```

---

## Integration with Claude Code

### How Claude Code Uses Claude-Flow

```
┌──────────────────────────────────────────────┐
│        You Chat with Claude Code             │
└──────────────────────────────────────────────┘
                   ↓
         Natural Language Processing
                   ↓
┌──────────────────────────────────────────────┐
│    Claude Detects: Need specialized help     │
│    Options:                                  │
│    1. Use a Skill (natural language)         │
│    2. Call MCP Tool (structured)             │
│    3. Spawn agents (complex task)            │
└──────────────────────────────────────────────┘
                   ↓
         ┌─────────┴─────────┐
         ↓                   ↓
    Skill System      MCP Tool System
         ↓                   ↓
  Auto-activated     Explicit function calls
  (transparent)      (mcp__claude-flow__*)
         ↓                   ↓
         └─────────┬─────────┘
                   ↓
            Claude-Flow Platform
                   ↓
          Agents Execute Tasks
                   ↓
          Results to Claude Code
                   ↓
        You See the Results
```

### Example Interactions

#### Simple Request (Skill Auto-Activation)
```
You: "Review this code for security issues"

Claude Code:
1. Detects: github-code-review skill needed
2. Automatically activates skill
3. Runs code review
4. Shows results

(You never knew a skill was activated - it just works!)
```

#### Complex Request (MCP Tool + Swarm)
```
You: "Build a full-stack app with React and Node"

Claude Code:
1. Recognizes: Complex multi-part task
2. Calls: mcp__claude-flow__swarm_init
3. Spawns: 6 agents (frontend, backend, db, test, review, docs)
4. Monitors: Progress through memory
5. Shows: Real-time updates
6. Delivers: Complete application

(Multi-agent coordination handled automatically!)
```

---

## Practical Examples

### Example 1: Pair Programming Session

**What You Do:**
```
You: "Let's pair program on user authentication"
```

**What Happens:**
```
1. pair-programming skill activates
2. Creates interactive session
3. You can:
   - /driver mode: You write, AI guides
   - /navigator mode: AI writes, you guide
   - /switch mode: Alternate every 10 mins

4. Real-time features:
   - Code suggestions
   - Security scanning
   - Auto-formatting
   - Test generation
   - Quality scoring
```

### Example 2: Multi-Agent Swarm

**What You Do:**
```
You: "Analyze this codebase and suggest optimizations"
```

**What Happens:**
```
Swarm spawned:
├── code-analyzer: Scans codebase structure
├── perf-analyzer: Identifies bottlenecks
├── security-agent: Finds vulnerabilities
├── test-analyzer: Checks coverage
└── reviewer: Compiles recommendations

All work in parallel, share findings via memory,
produce comprehensive report.
```

### Example 3: GitHub PR Review

**What You Do:**
```
You: "Review PR #123 in owner/repo"
```

**What Happens:**
```
1. github-code-review skill activates
2. Spawns specialized agents:
   - code-reviewer: Code quality
   - security-scanner: Vulnerabilities
   - test-checker: Test coverage
   - docs-checker: Documentation

3. Agents analyze in parallel
4. Generate detailed review comments
5. Can auto-post to GitHub (if configured)
```

---

## Under the Hood

### Memory System Internals

**SQLite Schema:**
```sql
-- Patterns table
CREATE TABLE patterns (
  id TEXT PRIMARY KEY,
  content TEXT,
  metadata TEXT,
  created_at INTEGER
);

-- Embeddings table (for semantic search)
CREATE TABLE embeddings (
  id TEXT PRIMARY KEY,
  pattern_id TEXT,
  embedding BLOB,  -- 1024-dim hash vector
  FOREIGN KEY(pattern_id) REFERENCES patterns(id)
);

-- Trajectories table (decision paths)
CREATE TABLE trajectories (
  id TEXT PRIMARY KEY,
  steps TEXT,
  outcome TEXT
);
```

**Semantic Search:**
```typescript
// Hash-based embeddings (no API needed)
const embed = (text: string): number[] => {
  // Creates deterministic 1024-dim vector
  return hashToVector(text);
};

// Search with MMR (Maximal Marginal Relevance)
const search = async (query: string) => {
  const queryVector = embed(query);
  
  // Find similar vectors (cosine similarity)
  const results = await db.findSimilar(queryVector, k=3);
  
  // Rank by 4 factors:
  // 1. Semantic similarity
  // 2. Recency
  // 3. Usage frequency
  // 4. Confidence score
  
  return rankedResults;
};
```

### Agent Execution Engine

**How Agents Run:**
```typescript
class AgentExecutor {
  async execute(agent: Agent, task: Task) {
    // 1. Pre-hooks
    await runHooks(agent.hooks.pre, { task });
    
    // 2. Check memory for context
    const context = await memory.retrieve(`agent/${agent.name}/context`);
    
    // 3. Execute main task
    const result = await agent.run(task, context);
    
    // 4. Store results
    await memory.store(`agent/${agent.name}/result`, result);
    
    // 5. Post-hooks
    await runHooks(agent.hooks.post, { result });
    
    // 6. Update metrics
    await updateMetrics(agent.name, result);
    
    return result;
  }
}
```

### Swarm Coordination

**Topology Management:**
```typescript
class SwarmCoordinator {
  async orchestrate(task: Task, topology: 'mesh' | 'hierarchical' | 'adaptive') {
    // 1. Decompose task
    const subtasks = await this.decompose(task);
    
    // 2. Assign agents
    const assignments = await this.assign(subtasks, topology);
    
    // 3. Execute in parallel
    const results = await Promise.all(
      assignments.map(async ({ agent, subtask }) => {
        // Each agent runs independently
        return await agentExecutor.execute(agent, subtask);
      })
    );
    
    // 4. Collect and merge
    return await this.merge(results);
  }
  
  async assign(subtasks, topology) {
    if (topology === 'mesh') {
      // All agents equal, distributed assignment
      return distributeEvenly(subtasks);
    } else if (topology === 'hierarchical') {
      // Queen assigns to specialized workers
      return await queenCoordinator.assign(subtasks);
    } else {
      // Auto-select best topology
      return await this.selectOptimalTopology(subtasks);
    }
  }
}
```

---

## Performance Stats

- **84.8% SWE-Bench solve rate** - Solves complex coding problems
- **32.3% token reduction** - Efficient context management
- **2.8-4.4x speed improvement** - Parallel agent execution
- **2-3ms query latency** - Fast memory retrieval
- **95%+ code quality** - With verification enabled

---

## Summary

Claude-Flow works by:

1. **Detecting your intent** through natural language
2. **Activating skills** automatically based on what you need
3. **Spawning specialized agents** for complex tasks
4. **Coordinating work** through shared memory
5. **Running agents in parallel** for speed
6. **Using hooks** for automation
7. **Delivering results** back to you through Claude Code

The beauty is: **Most of this is invisible to you**. You just chat naturally with Claude Code, and Claude-Flow orchestrates everything behind the scenes!

---

## Next Steps

1. **Try a simple command:**
   ```bash
   node bin/claude-flow.js swarm "analyze this code" --claude
   ```

2. **Activate a skill:**
   Just chat with Claude Code: "Let's pair program"

3. **Explore agents:**
   ```bash
   ls .claude/agents/
   cat .claude/agents/core/coder.md
   ```

4. **Read skill docs:**
   ```bash
   cat .claude/skills/pair-programming/SKILL.md
   ```

5. **Check memory:**
   ```bash
   node bin/claude-flow.js memory status --reasoningbank
   ```

---

**Questions?**
- Read more docs: `docs/`
- Check command reference: `.claude/commands/`
- Join Discord: https://discord.com/invite/dfxmpwkG2D
- GitHub: https://github.com/ruvnet/claude-flow

