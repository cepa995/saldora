1. Create PHASE X branch in github repository, if it doesn't already exist
2. Create MILESTONE X in github repository, if it doesn't already exist
3. Create a new ISSUE from the previously created MILESTONE X and assign it to yourself
4. Complete the task and checkout new branch: 
    4.1. `git checkout -b feature/[issue-id]-[name]` 
    4.2. `git add . && git commit -m "[MESSAGE]"`
    4.3. `git push -u origin HEAD`
5. Create PR: `feature/[issue-id]-[name]` -> `phase_x`
6. Create PR: `phase_x` -> `main` once entire PHASE X has been implemented