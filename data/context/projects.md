# YASH PROJECT PROFILES

## Project Name: GDSC Search Engine

### Origin Story
GDSC had an open project focused on improving search across their learning resources and documentation.
I picked up the project and decided to solve it.

### Problem
The existing search experience relied primarily on BM25 keyword search across documents.
Students often had to know the exact keywords to find relevant information, and navigating large collections of PDFs could be cumbersome.

### Goal
Build a more natural way for students to interact with the knowledge base by allowing them to ask questions and receive answers directly from the documents.

### What I Thought Would Be Hard
At first, I thought the difficult part would be integrating the LLM and building the chat experience.

### What Was Actually Hard
The harder problem turned out to be retrieval.
The model could only generate useful answers if the right context was retrieved first.
I ended up spending much more time thinking about retrieval quality, ranking, and combining semantic search with keyword search than I initially expected.

### Interesting Realization
I realized that improving retrieval often had a larger impact on answer quality than changing the language model itself.
The quality of the context mattered more than the sophistication of the model.

### What I Built
A hybrid search system that combined semantic retrieval and keyword search.
Instead of manually searching through PDFs, users could ask questions naturally and receive context-aware answers from the document collection.

### What This Project Says About Me
I enjoy taking ownership of open-ended problems.
I tend to start with a practical problem and then work backward to design a system that solves it.
I also learned that many AI applications succeed or fail based on the quality of their retrieval pipeline rather than the model alone.

### Role Relevance
AI Engineer, LLM Engineer, Applied AI Engineer, ML Engineer, Backend Engineer, Software Engineer

---

## Project Name: YAAR

### Origin Story
The idea did not start as a social app.
It started with a much simpler question:
"Why does everyone consume the same content even though people are interested in completely different things?"
I became interested in personalization and how technology could create more relevant experiences for individuals rather than showing everyone the same thing.

### Initial Idea
The original focus was personalized content creation.
The goal was to create a system that could understand user preferences and generate content tailored specifically to the individual.
As I explored the problem further, I realized the interesting challenge wasn't generating content.
The interesting challenge was understanding the user.

### Problem
Most digital products focus heavily on content generation.
I realized that personalization is often the bigger problem.
Generating content is relatively easy.
Understanding what someone actually wants to see is much harder.

### What I Thought Would Be Hard
Initially, I thought content generation and AI would be the difficult part.

### What Was Actually Hard
The harder problem turned out to be personalization.
Questions started appearing:
- How do you model preferences?
- How do you understand changing interests?
- How do you avoid showing repetitive content?
- How do you balance relevance with discovery?

I spent much more time thinking about user behavior and recommendation logic than content generation itself.

### Interesting Realization
I realized that personalization is often more valuable than creation.
People don't necessarily need more content.
They need better content selection.
The bottleneck is frequently relevance, not generation.

### What I Built
YAAR evolved into a platform focused on personalized experiences, using user behavior, interests, and context to create more relevant interactions.

### What This Project Says About Me
I enjoy starting with a problem and refining it repeatedly until I find the actual bottleneck.
I tend to question assumptions.
In this case, I started by thinking content creation was the problem and eventually realized personalization was the real opportunity.

### Role Relevance
Product Management, AI Product Management, Software Engineering, Recommendation Systems, Consumer Products, Growth, Applied AI

---

## Project Name: EchoPod

### Origin Story
The idea started from a simple observation.
There is an enormous amount of valuable information available online, but consuming it requires time and attention that people often don't have.
I noticed that many articles, blogs, newsletters, and long-form content were being saved but never actually consumed.

### Problem
People frequently discover useful content but postpone reading it.
Bookmarks pile up.
Read-later lists grow.
Most content never gets consumed.
The problem wasn't access to information.
The problem was convenience.

### What I Thought Would Be Hard
Initially, I thought the difficult part would be content generation and audio conversion.

### What Was Actually Hard
The harder challenge was creating an experience that felt natural.
Questions started appearing:
- What content is worth converting?
- How should information be summarized?
- How much detail should be preserved?
- How do you make audio consumption feel useful rather than repetitive?

The challenge became balancing convenience with information quality.

### Interesting Realization
I realized that people often don't have an information problem.
They have a time and attention problem.
Making knowledge more accessible can be more valuable than creating new knowledge.

### What I Built
EchoPod converts written content into a more accessible audio-first experience, allowing users to consume information while commuting, walking, exercising, or performing other activities.
The goal was to reduce friction between discovering information and actually consuming it.

### What This Project Says About Me
I enjoy identifying friction in everyday workflows.
Rather than asking how to create more content, I often ask how to make existing content easier to use.
This project reinforced the idea that improving accessibility and convenience can sometimes create more value than adding new features.

### Role Relevance
Product Management, Consumer Products, AI Product Management, Software Engineering, Applied AI, Content Platforms, Creator Economy
