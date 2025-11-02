
import { GoogleGenAI, Modality } from "@google/genai";
import { base64ToDataAndMimeType } from '../utils/imageUtils';

if (!process.env.API_KEY) {
    throw new Error("API_KEY environment variable is not set");
}

const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

export const enhanceImageWithPrompt = async (base64Image: string, mimeType: string, prompt: string): Promise<string> => {
    try {
        const { data } = base64ToDataAndMimeType(base64Image);

        const response = await ai.models.generateContent({
            model: 'gemini-2.5-flash-image',
            contents: {
                parts: [
                    {
                        inlineData: {
                            data: data,
                            mimeType: mimeType,
                        },
                    },
                    {
                        text: prompt,
                    },
                ],
            },
            config: {
                responseModalities: [Modality.IMAGE],
            },
        });

        const imagePart = response.candidates?.[0]?.content?.parts?.find(part => part.inlineData);
        if (imagePart && imagePart.inlineData) {
            const newBase64Data = imagePart.inlineData.data;
            const newMimeType = imagePart.inlineData.mimeType;
            return `data:${newMimeType};base64,${newBase64Data}`;
        } else {
            throw new Error('No image data returned from API.');
        }
    } catch (error) {
        console.error('Gemini API call failed:', error);
        throw new Error('Failed to enhance image with AI. Please check the console for more details.');
    }
};
