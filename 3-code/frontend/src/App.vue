<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <header>
    <nav>
      <RouterLink to="/">Library</RouterLink>
      <RouterLink to="/create">Create</RouterLink>
      <RouterLink to="/models">Models</RouterLink>
      <RouterLink to="/preview">Preview</RouterLink>
      <RouterLink to="/monitoring">Monitoring</RouterLink>
    </nav>
  </header>

  <main>
    <RouterView />
  </main>
</template>
