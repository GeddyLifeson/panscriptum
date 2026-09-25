# Finishing the era chapters on a local Ollama model

101 chapters are missing (ages I, II, III, IV, VI, VII; age V is complete). On a machine with Ollama:

```
git fetch origin claude/beautiful-fermat-9xu33t && git checkout claude/beautiful-fermat-9xu33t && git pull
cd reference/owner_source_material/rodais
ollama list                                   # pick the biggest instruct model you have (32B+ if possible)
python3 eras/ollama_writer.py --list          # what is missing
python3 eras/ollama_writer.py --model <model> # writes them all; resumable, rerun to continue
```

Each chapter: scene plan -> 5-7 scenes of ~900 words -> tells/future checks with one repair pass -> events JSON.
Nothing existing is overwritten (half-written chapters without an events file are redone).
When done: `git add -A eras && git commit -m "Era chapters from local model" && git push`.
The volumes then need the lead's pass (chronicle, back matter, continuity, build), done in the cloud session.
