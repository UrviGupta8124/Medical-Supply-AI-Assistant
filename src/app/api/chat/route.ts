import { createGroq } from '@ai-sdk/groq';
import { streamText } from 'ai';
import { verifiedMedicines } from '@/data/medicines';

const groq = createGroq({
  apiKey: process.env.GROQ_API_KEY,
});

// Simple mock retrieval function based on keywords
function retrieveContext(query: string) {
  const lowercaseQuery = query.toLowerCase();
  
  // Find medicines whose name, class, or indications match the query words
  const queryWords = lowercaseQuery.split(' ').filter(w => w.length > 3);
  
  const matches = verifiedMedicines.filter(med => {
    const textToSearch = `${med.name} ${med.class} ${med.indications.join(' ')} ${med.defenseContext}`.toLowerCase();
    return queryWords.some(word => textToSearch.includes(word));
  });

  // If no specific match, return a general warning or top matches.
  if (matches.length === 0) {
    return "No specific medical records found for the query in the verified database. Advise the user to consult standard medical protocols or clarify their query.";
  }

  // Format matches into a readable context
  return matches.map(med => `
    Name: ${med.name}
    Class: ${med.class}
    Indications: ${med.indications.join(', ')}
    Dosage: ${med.dosage}
    Side Effects: ${med.sideEffects.join(', ')}
    Contraindications: ${med.contraindications.join(', ')}
    Defense Context: ${med.defenseContext}
  `).join('\n\n');
}

export async function POST(req: Request) {
  const { messages } = await req.json();
  const latestMessage = messages[messages.length - 1];
  
  // Retrieve relevant context based on the latest user message
  const context = retrieveContext(latestMessage.content);

  const systemPrompt = `You are a highly secure, defense-focused medical AI assistant.
Your purpose is to provide medical information strictly based on the provided verified database context.
Do not hallucinate or provide medical advice outside of this context.
If the context does not contain the answer, explicitly state that you cannot find the information in the verified database.
Maintain a professional, precise, and authoritative tone suitable for defense personnel.

VERIFIED MEDICAL CONTEXT:
${context}
`;

  // Call Groq using Vercel AI SDK
  const result = await streamText({
    model: groq('llama-3.1-8b-instant'), // Using a fast, reliable model on Groq
    system: systemPrompt,
    messages,
  });

  return result.toTextStreamResponse();
}
