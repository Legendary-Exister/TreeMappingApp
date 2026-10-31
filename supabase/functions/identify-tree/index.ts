import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req: Request) => {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const { photoUrl, organs } = await req.json();

    if (!photoUrl) {
      return new Response(JSON.stringify({ error: 'Missing photoUrl in request body' }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const plantnetKey = Deno.env.get('PLANTNET_API_KEY');
    if (!plantnetKey) {
      // Mock response for development when API key is not configured
      return new Response(
        JSON.stringify({
          status: 'mock',
          message: 'Pl@ntNet API key not set. Returning mock species suggestions.',
          results: [
            {
              score: 0.89,
              species: {
                scientificNameWithoutAuthor: 'Quercus robur',
                scientificName: 'Quercus robur L.',
                genus: { scientificNameWithoutAuthor: 'Quercus' },
                family: { scientificNameWithoutAuthor: 'Fagaceae' },
                commonNames: ['English Oak', 'Pedunculate Oak', 'Stieleiche'],
              },
            },
            {
              score: 0.72,
              species: {
                scientificNameWithoutAuthor: 'Tilia cordata',
                scientificName: 'Tilia cordata Mill.',
                genus: { scientificNameWithoutAuthor: 'Tilia' },
                family: { scientificNameWithoutAuthor: 'Malvaceae' },
                commonNames: ['Small-leaved Lime', 'Winterlinde'],
              },
            },
          ],
        }),
        {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        }
      );
    }

    // Call official Pl@ntNet API endpoint
    const url = new URL('https://my-api.plantnet.org/v2/identify/all');
    url.searchParams.append('api-key', plantnetKey);
    url.searchParams.append('images', photoUrl);
    url.searchParams.append('organs', organs || 'leaf');

    const plantNetResponse = await fetch(url.toString());
    const data = await plantNetResponse.json();

    return new Response(JSON.stringify(data), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (err: unknown) {
    const error = err as Error;
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
