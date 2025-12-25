The Real Problem
AWS prioritizes enterprise flexibility over developer simplicity. They assume you want to customize everything, so they make everything customizable - even basic authentication. This creates:

Analysis paralysis - too many options for simple use cases
Maintenance burden - breaking changes every major version
Knowledge silos - requires AWS-specific expertise for standard features
Better Alternatives
For most applications, simpler solutions work better:

Auth0 - Just works, good docs, stable APIs
Firebase Auth - Simple integration, fewer breaking changes
Supabase - PostgreSQL + auth, straightforward setup
NextAuth.js - If using Next.js, much simpler
Your frustration is completely justified. AWS makes simple things complex, and then charges you for the complexity they created.
