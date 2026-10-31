import React from 'react';
import { StyleSheet, Text, View, SafeAreaView } from 'react-native';
import { StatusBar } from 'expo-status-bar';

export default function App() {
  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="dark" />
      <View style={styles.content}>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>TreeMap Mobile</Text>
        </View>
        <Text style={styles.title}>Urban Tree Explorer</Text>
        <Text style={styles.subtitle}>
          Citizen science tree mapping powered by OpenStreetMap, MapLibre, and PostGIS.
        </Text>
        <View style={styles.card}>
          <Text style={styles.cardHeader}>Mobile Placeholder</Text>
          <Text style={styles.cardText}>
            Expo + TypeScript mobile placeholder screen.
          </Text>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  content: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  badge: {
    backgroundColor: '#dcfce7',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 16,
    marginBottom: 12,
  },
  badgeText: {
    color: '#15803d',
    fontWeight: '700',
    fontSize: 12,
    textTransform: 'uppercase',
  },
  title: {
    fontSize: 28,
    fontWeight: '800',
    color: '#0f172a',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 15,
    color: '#64748b',
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 22,
  },
  card: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 20,
    width: '100%',
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  cardHeader: {
    fontSize: 16,
    fontWeight: '700',
    color: '#166534',
    marginBottom: 6,
  },
  cardText: {
    fontSize: 14,
    color: '#334155',
    lineHeight: 20,
  },
});
