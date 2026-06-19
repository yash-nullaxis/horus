import { OpencodeClient } from '@opencode-ai/sdk/v2/client';

const run = async () => {
    const client = new OpencodeClient({ baseUrl: 'http://127.0.0.1:8787' });

    console.log("Creating session...");
    const sessionRes = await client.session.create({ body: {} });

    if (sessionRes.error) {
        console.error("Error creating session:", sessionRes.error);
        process.exit(1);
    }

    const sessionId = sessionRes.data.id;
    console.log(`Session created: ${sessionId}`);

    console.log("Sending prompt to OpenWork...");
    const promptRes = await client.session.prompt({
        path: { id: sessionId },
        body: {
            message: "Write e2e tests using playwright for this project. Ensure you provide a clear command or script I can run locally to execute these tests using playwright. Install playwright and dependencies if they are missing."
        }
    });

    if (promptRes.error) {
         console.error("Error sending prompt:", promptRes.error);
         process.exit(1);
    }

    console.log("Prompt sent! Wait for the agent to finish...");

    let isFinished = false;
    while (!isFinished) {
        await new Promise(resolve => setTimeout(resolve, 5000));

        const statusRes = await client.session.status({ path: { id: sessionId }});
        if (statusRes.error) {
            console.error("Error checking status:", statusRes.error);
            continue;
        }

        const state = statusRes.data.state;
        if (state === "finished" || state === "error" || state === "stopped" || state === "complete") {
             console.log(`Session finished with state: ${state}`);
             isFinished = true;
        } else {
             console.log(`Current state: ${state} - agent is working...`);
        }
    }

    console.log("OpenWork task finished successfully!");
};

run().catch(err => {
    console.error("Fatal error:", err);
    process.exit(1);
});
