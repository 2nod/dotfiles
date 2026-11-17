module.exports = async function capture(client, savedRevision) {
  const page = await client.firstPage();
  const latest = page.data.filter(e => e.type === 'user.message').at(-1);
  return { messageRevision: latest?.revision ?? null,
    matchesSaved: latest?.revision === savedRevision };
};
