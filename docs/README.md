# 📚 Claude-Flow Documentation Hub

Welcome to the Claude-Flow documentation! This guide will help you understand how everything works.

## 🚀 Start Here

### New to Claude-Flow?
1. **[Quick Start Setup](./QUICK-START-SETUP.md)** - Installation complete, what's next?
2. **[How It Works](./HOW-IT-WORKS.md)** - Comprehensive architecture guide
3. **[Quick Reference](./QUICK-REFERENCE.md)** - Cheat sheet for commands and concepts

### Visual Learner?
- **[Architecture Diagram](./ARCHITECTURE-DIAGRAM.md)** - Complete system architecture with diagrams

---

## 📖 Documentation Structure

```
docs/
├── README.md (you are here)
│
├── Getting Started
│   ├── QUICK-START-SETUP.md      # Setup complete, what's next?
│   ├── QUICK-REFERENCE.md         # Quick reference card
│   └── skills-tutorial.md         # Skills system guide
│
├── Understanding Claude-Flow
│   ├── HOW-IT-WORKS.md           # Complete explanation
│   └── ARCHITECTURE-DIAGRAM.md    # Visual diagrams
│
└── Reference
    ├── RELEASE_v2.7.1.md         # Current version
    └── RELEASE-NOTES-*.md        # Version history
```

---

## 🎯 Quick Links by Topic

### Understanding the System
- **How does Claude-Flow work?** → [HOW-IT-WORKS.md](./HOW-IT-WORKS.md)
- **What are Skills?** → [skills-tutorial.md](./skills-tutorial.md)
- **System architecture?** → [ARCHITECTURE-DIAGRAM.md](./ARCHITECTURE-DIAGRAM.md)

### Using Claude-Flow
- **Quick commands?** → [QUICK-REFERENCE.md](./QUICK-REFERENCE.md)
- **Setup guide?** → [QUICK-START-SETUP.md](./QUICK-START-SETUP.md)
- **Command docs?** → `../.claude/commands/`

### Advanced Topics
- **Agent definitions?** → `../.claude/agents/`
- **Skill definitions?** → `../.claude/skills/`
- **MCP integration?** → [HOW-IT-WORKS.md#integration-with-claude-code](./HOW-IT-WORKS.md)

---

## 🧠 Core Concepts Explained

### 5 Key Components

1. **Skills (25)** - Auto-activated capabilities
   - Just chat naturally
   - Skills detect intent
   - No commands needed
   - [Learn more →](./HOW-IT-WORKS.md#1-skills-25-total)

2. **Agents (64)** - Specialized workers
   - Coder, tester, reviewer, etc.
   - Work in parallel
   - Coordinate via memory
   - [Learn more →](./HOW-IT-WORKS.md#2-agents-64-total)

3. **Swarms** - Multi-agent teams
   - Mesh, hierarchical, adaptive
   - Automatic coordination
   - Shared memory
   - [Learn more →](./HOW-IT-WORKS.md#3-swarms)

4. **Memory (ReasoningBank)** - Persistent storage
   - SQLite database
   - 2-3ms semantic search
   - Cross-agent coordination
   - [Learn more →](./HOW-IT-WORKS.md#4-memory-system-reasoningbank)

5. **MCP Tools (100+)** - Claude Code integration
   - Function calls
   - Swarm orchestration
   - GitHub automation
   - [Learn more →](./HOW-IT-WORKS.md#5-mcp-tools-100-total)

---

## 🎓 Learning Paths

### Beginner Path
```
1. Read QUICK-START-SETUP.md
2. Try: node bin/claude-flow.js swarm "hello world"
3. Explore: .claude/agents/core/
4. Read: QUICK-REFERENCE.md
```

### Intermediate Path
```
1. Read HOW-IT-WORKS.md (sections 1-4)
2. Try: Multi-agent swarms
3. Explore: Skills system
4. Read: skills-tutorial.md
```

### Advanced Path
```
1. Read complete HOW-IT-WORKS.md
2. Study: ARCHITECTURE-DIAGRAM.md
3. Try: Custom agent configurations
4. Explore: MCP tool integration
```

---

## 💡 Quick Examples

### Example 1: Simple Task
```bash
# Just run a swarm
node bin/claude-flow.js swarm "build a REST API" --claude
```

### Example 2: Natural Language (in Claude Code)
```
You: "Let's pair program on this feature"
→ pair-programming skill activates automatically
```

### Example 3: Memory Usage
```bash
# Store information
node bin/claude-flow.js memory store api "REST config" --reasoningbank

# Query later
node bin/claude-flow.js memory query "API" --reasoningbank
```

---

## 📊 How Everything Connects

```
You
 ↓
Claude Code (detects intent)
 ↓
Skills (auto-activate) OR MCP Tools (explicit calls)
 ↓
Swarm Orchestration (task decomposition)
 ↓
Agents (parallel execution)
 ↓
Memory (coordination)
 ↓
Results back to you
```

[See detailed diagrams →](./ARCHITECTURE-DIAGRAM.md)

---

## 🔍 Find What You Need

### I want to...

**Understand the system:**
- How does it work? → [HOW-IT-WORKS.md](./HOW-IT-WORKS.md)
- See architecture → [ARCHITECTURE-DIAGRAM.md](./ARCHITECTURE-DIAGRAM.md)
- Quick overview → [QUICK-REFERENCE.md](./QUICK-REFERENCE.md)

**Use the system:**
- Get started → [QUICK-START-SETUP.md](./QUICK-START-SETUP.md)
- Command reference → [QUICK-REFERENCE.md](./QUICK-REFERENCE.md)
- Learn skills → [skills-tutorial.md](./skills-tutorial.md)

**Dive deeper:**
- Agent system → `../.claude/agents/`
- Skill definitions → `../.claude/skills/`
- Command docs → `../.claude/commands/`

---

## 🎯 Key Takeaways

1. **Skills auto-activate** - Just chat naturally with Claude Code
2. **Agents work in parallel** - Multiple specialists on one task
3. **Memory coordinates** - Agents share knowledge automatically
4. **It just works** - Complexity is hidden from you

---

## 📞 Need Help?

- **Question about concepts?** → Read [HOW-IT-WORKS.md](./HOW-IT-WORKS.md)
- **Need quick reference?** → Check [QUICK-REFERENCE.md](./QUICK-REFERENCE.md)
- **Command not working?** → See `../.claude/commands/`
- **GitHub Issues:** https://github.com/ruvnet/claude-flow/issues
- **Discord Community:** https://discord.com/invite/dfxmpwkG2D

---

## 📝 Documentation Versions

- **Current:** v2.7.1
- **Release Notes:** [RELEASE_v2.7.1.md](./RELEASE_v2.7.1.md)
- **Latest Alpha:** v2.7.0-alpha.10
- **Changelog:** [../CHANGELOG.md](../CHANGELOG.md)

---

**Ready to start?** Pick a guide from above and dive in! 🚀

**Quick test:**
```bash
node bin/claude-flow.js --version
node bin/claude-flow.js memory status --reasoningbank
```
