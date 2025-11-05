# 🚀 Claude-Flow Quick Reference Card

## 🎯 What Is Claude-Flow?

**An AI orchestration platform that lets multiple AI agents work together on complex tasks.**

```
You → Claude Code → Claude-Flow → Multiple AI Agents → Your Project Built
```

---

## 🧩 Key Components

### 1. Skills (25) - Auto-Activated
Natural language capabilities that Claude detects automatically.

| Skill | Trigger Phrase | What It Does |
|-------|---------------|--------------|
| pair-programming | "Let's pair program" | Interactive coding session |
| swarm-orchestration | "Build with multiple agents" | Spawns agent teams |
| github-code-review | "Review this PR" | Automated code review |
| agentdb-vector-search | "Search similar code" | Semantic code search |

### 2. Agents (64) - Specialized Workers

| Agent | Role | Used For |
|-------|------|----------|
| coder | Implementation | Writing code |
| tester | Testing | Creating tests |
| reviewer | Quality | Code review |
| researcher | Analysis | Research & planning |
| backend-dev | Backend | API development |
| security-manager | Security | Security audits |

### 3. Swarms - Multi-Agent Teams

| Topology | Structure | Best For |
|----------|-----------|----------|
| Mesh | Peer-to-peer | Equal collaboration |
| Hierarchical | Queen + Workers | Complex projects |
| Adaptive | Auto-switching | Unknown complexity |

### 4. Memory - Persistent Storage

| Type | Storage | Speed |
|------|---------|-------|
| ReasoningBank | SQLite | 2-3ms |
| Semantic Search | Hash embeddings | No API needed |
| Namespaces | Organized | By domain |

### 5. MCP Tools (100+) - Function Calls

| Category | Example | Purpose |
|----------|---------|---------|
| Swarm | `swarm_init` | Start coordination |
| Memory | `memory_usage` | Store/retrieve data |
| GitHub | `github_swarm` | Repo automation |
| Performance | `benchmark_run` | Measure speed |

---

## ⚡ Quick Commands

### Basic Usage
```bash
# Version check
node bin/claude-flow.js --version

# Simple swarm
node bin/claude-flow.js swarm "build REST API" --claude

# Hive-mind (complex)
node bin/claude-flow.js hive-mind wizard

# Memory check
node bin/claude-flow.js memory status --reasoningbank
```

### Memory Operations
```bash
# Store
node bin/claude-flow.js memory store api_key "REST config" --reasoningbank

# Query
node bin/claude-flow.js memory query "API" --reasoningbank

# List
node bin/claude-flow.js memory list --reasoningbank
```

### Agent Commands
```bash
# Spawn specific agent
node bin/claude-flow.js agent spawn coder --task "implement auth"

# List agents
ls .claude/agents/

# View agent details
cat .claude/agents/core/coder.md
```

### GitHub Integration
```bash
# Analyze repo
node bin/claude-flow.js github analyze owner/repo

# Review PR
node bin/claude-flow.js github pr-review owner/repo 123

# Setup
./.claude/helpers/github-setup.sh
```

---

## 🔄 Typical Workflows

### Workflow 1: Feature Development
```
1. You: "Build user authentication"
2. Swarm spawns: researcher, backend-dev, tester, reviewer
3. Agents work in parallel using shared memory
4. Result: Complete feature with tests
```

### Workflow 2: Code Review
```
1. You: "Review this code for issues"
2. Skill activates: code-review
3. Multiple reviewers check: security, performance, style
4. Result: Detailed review report
```

### Workflow 3: Bug Fixing
```
1. You: "Find and fix the memory leak"
2. Swarm spawns: debugger-expert, perf-analyzer
3. Agents analyze and propose fixes
4. Result: Bug fixed with tests
```

---

## 📊 Execution Flow

```
Step 1: You make request
   ↓
Step 2: Claude Code analyzes intent
   ↓
Step 3: Skill auto-activates OR MCP tool called
   ↓
Step 4: Claude-Flow receives request
   ↓
Step 5: Task decomposed into subtasks
   ↓
Step 6: Agents assigned to subtasks
   ↓
Step 7: Agents execute in parallel
   ↓
Step 8: Results stored in memory
   ↓
Step 9: Coordinator assembles results
   ↓
Step 10: Response to you via Claude Code
```

---

## 🧠 How Agents Coordinate

```
┌──────────────────────────────────────┐
│      Shared Memory (SQLite)          │
│                                      │
│  ┌────────────────────────────────┐ │
│  │ Agent A: Stores API design     │ │
│  └────────────────────────────────┘ │
│              ↓                       │
│  ┌────────────────────────────────┐ │
│  │ Agent B: Reads design          │ │
│  │         Writes tests           │ │
│  └────────────────────────────────┘ │
│              ↓                       │
│  ┌────────────────────────────────┐ │
│  │ Agent C: Reads tests           │ │
│  │         Reviews code           │ │
│  └────────────────────────────────┘ │
└──────────────────────────────────────┘
```

**Key Point:** All agents share information through memory, enabling coordination without direct communication.

---

## 💡 Pro Tips

### 1. Use Natural Language
```
❌ Don't: "Run mcp__claude-flow__swarm_init with mesh topology"
✅ Do: "Use multiple agents to build this"
```

### 2. Enable ReasoningBank
```bash
# Always use --reasoningbank for persistent memory
node bin/claude-flow.js memory store key "value" --reasoningbank
```

### 3. Let Claude Detect Skills
```
Just chat naturally - skills activate automatically!
```

### 4. Check Documentation
```bash
# 104 command docs available
ls .claude/commands/

# Read specific command
cat .claude/commands/swarm/swarm-quick-start.md
```

### 5. Use --claude Flag
```bash
# For best integration with Claude Code
node bin/claude-flow.js swarm "task" --claude
```

---

## 🔍 Understanding MCP Tools

### What Are They?
Functions that Claude Code can call to interact with Claude-Flow.

### How They Work
```javascript
// When you chat with Claude Code...
You: "Start a swarm to build an API"

// Claude Code calls:
mcp__claude-flow__swarm_init({
  topology: "adaptive",
  maxAgents: 5
})

// Claude-Flow executes:
- Spawns agents
- Distributes tasks
- Coordinates work
- Returns results

// You see:
"✅ API built successfully!"
```

### Categories
- **Coordination**: `swarm_init`, `agent_spawn`, `task_orchestrate`
- **Memory**: `memory_usage`, `memory_search`
- **GitHub**: `github_swarm`, `repo_analyze`, `pr_enhance`
- **Performance**: `benchmark_run`, `bottleneck_analyze`
- **Neural**: `neural_status`, `neural_train`

---

## 📁 File Structure

```
claude-flow/
├── .claude/               # Configuration
│   ├── agents/           # 64 agent definitions
│   ├── skills/           # 25 skill definitions
│   ├── commands/         # 104 command docs
│   └── settings.json     # Main config
├── .swarm/
│   └── memory.db         # Persistent memory (SQLite)
├── bin/
│   └── claude-flow.js    # CLI entry point
├── docs/                 # Documentation
│   ├── HOW-IT-WORKS.md  # This guide!
│   └── QUICK-REFERENCE.md
└── CLAUDE.md            # Claude Code config
```

---

## 🎓 Learning Path

### Beginner
1. Read: `docs/QUICK-START-SETUP.md`
2. Try: `node bin/claude-flow.js swarm "hello world"`
3. Explore: `.claude/agents/core/`

### Intermediate
1. Read: `docs/HOW-IT-WORKS.md`
2. Try: Multi-agent swarms
3. Explore: Skills system

### Advanced
1. Read: `.claude/skills/*/SKILL.md`
2. Try: Custom agents
3. Explore: MCP tool integration

---

## 🐛 Common Issues

### Issue: MCP servers not connecting
```bash
# Check configuration
cat ~/.claude.json

# Restart Claude Code
```

### Issue: Memory not persisting
```bash
# Check database exists
ls -la .swarm/memory.db

# Test memory system
node bin/claude-flow.js memory status --reasoningbank
```

### Issue: Skills not activating
```bash
# Use more explicit language
Instead of: "Do this thing"
Try: "Use swarm orchestration to build this"
```

---

## 📞 Support

- **Docs**: `/Users/aniksahai/Desktop/claude-flow/docs/`
- **Commands**: `.claude/commands/`
- **GitHub**: https://github.com/ruvnet/claude-flow
- **Discord**: https://discord.com/invite/dfxmpwkG2D
- **Issues**: https://github.com/ruvnet/claude-flow/issues

---

## 🎯 Quick Decision Tree

```
Need to...
│
├─ Build simple feature?
│  → Just chat with Claude Code (skills auto-activate)
│
├─ Build complex project?
│  → Use: node bin/claude-flow.js hive-mind wizard
│
├─ Review code?
│  → Say: "Review this code" (github-code-review skill)
│
├─ Test something?
│  → Use: tester agent or tdd-specialist
│
├─ Multiple tasks in parallel?
│  → Use: swarm with mesh topology
│
└─ Store information for later?
   → Use: memory store --reasoningbank
```

---

## 🌟 Key Takeaways

1. **Skills auto-activate** - Just chat naturally
2. **Agents work in parallel** - Faster execution
3. **Memory coordinates** - Agents share state
4. **MCP tools enable** - Claude Code integration
5. **Hooks automate** - Pre/post operations
6. **It just works** - Complexity is hidden

---

**Ready to use it?** Just start chatting with Claude Code in this project! 🚀

