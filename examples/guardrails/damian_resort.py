
#--------------------------------------------------------------------------------------------------------------------------------
# Ejemplo de implementación de un input guardrail para un agente de triage en Damian Resort Hotel
# y activa un tripwire si la entrada no es válida.
#---------------------------------------------------------------------------------------------------------------------------------


#----------------------------------------------------------------------------------------------------------------------------
# Paso 1: Instalar las dependencias necesarias
#----------------------------------------------------------------------------------------------------------------------------
import os
import asyncio

from dotenv import load_dotenv
from pydantic import BaseModel

from agents import (
    Agent,
    Runner,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    RunContextWrapper,
    TResponseInputItem,
    input_guardrail,
    set_default_openai_key,
    trace,
)
from prompt_agent import (
    booking_agent_instructions,
    billing_agent_instructions,
    maintenance_agent_instructions,
    guardrail_instructions,
    triage_instructions,
)


# ----------------------------------------------------------------------------------------------------------------------------
# Paso 2: Configurar las variables de entorno y la clave de OpenAI
# ----------------------------------------------------------------------------------------------------------------------------
# Asegúrate de tener un archivo .env con la variable OPENAI_API_KEY configurada
load_dotenv() 
openai_api_key = os.environ.get("OPENAI_API_KEY")
if openai_api_key is None:
    raise ValueError("OPENAI_API_KEY environment variable is not set.")
set_default_openai_key(openai_api_key)



# ----------------------------------------------------------------------------------------------------------------------------
# Paso 3: Definir el modelo de salida del guardrail
# ----------------------------------------------------------------------------------------------------------------------------
class GuardrailCheckOutput(BaseModel):
    is_valid_input: bool
    reasoning: str




    
# ----------------------------------------------------------------------------------------------------------------------------
# Paso 4: Crear el agente guardrail 
# ----------------------------------------------------------------------------------------------------------------------------
guardrail_agent = Agent(
    name="Guardrail check",
    instructions=guardrail_instructions,
    output_type=GuardrailCheckOutput, # Definimos el tipo de salida del guardrail 
    model="gpt-4.1-2025-04-14" # puse un modelo mas economico para pruebas
)



# ----------------------------------------------------------------------------------------------------------------------------
# Paso 5: Definir la función del input guardrail
# ----------------------------------------------------------------------------------------------------------------------------
@input_guardrail(name="customer_support_input_check")
async def support_input_guardrail(
    ctx: RunContextWrapper[None], # El contexto de ejecución
    agent: Agent, # El agente al que llega la entrada (en este caso, triage_agent) 
    input: str | list[TResponseInputItem] # La entrada del usuario 
) -> GuardrailFunctionOutput: # La función debe devolver GuardrailFunctionOutput 
   
    result = await Runner.run(
        starting_agent=guardrail_agent, # Usamos nuestro agente interno para el chequeo 
        input=input, # Le pasamos la entrada original del usuario
        context=ctx.context, # Pasamos el mismo contexto de ejecución
    )
    # Accedemos al resultado estructurado del agente verificador 
    final_output = result.final_output_as(GuardrailCheckOutput)

    # Activamos el tripwire si la entrada *no* es válida.
    tripwire_triggered = not final_output.is_valid_input
    # Retornamos el resultado del guardarraíl 
    return GuardrailFunctionOutput(
        output_info=final_output, # Opcionalmente incluimos la información del output del agente verificador 
        tripwire_triggered=tripwire_triggered, # Indicamos si el tripwire se activó 
    )

# ----------------------------------------------------------------------------------------------------------------------------
# Paso 6: Definir los agentes
# ----------------------------------------------------------------------------------------------------------------------------
booking_agent = Agent(
    name="Agente de Reservas del Damian Resort",
    instructions=booking_agent_instructions,
    handoff_description="""Un agente de reservas útil que procesa solicitudes relacionadas con la reservación de habitaciones en Damian Resort.""",
    model="gpt-4.1-2025-04-14" 
    # No agregue tools porque este ejemplo es sobre input guardrails, pero si desean pueden agregar herramientas aquí
)

billing_agent = Agent(
    name="Agente de Facturación del Damian Resort",
    instructions=billing_agent_instructions,
    handoff_description="""Un agente de facturación útil que asiste a los clientes con consultas sobre sus facturas en Damian Resort.""",
    model="gpt-4.1-2025-04-14" 
)

maintenance_agent = Agent(
    name="Agente de Mantenimiento del Damian Resort",
    instructions=maintenance_agent_instructions,
    handoff_description="""Un agente de mantenimiento útil que registra reportes de problemas de mantenimiento en Damian Resort.""",
    model="gpt-4.1-2025-04-14" 
)

triage_agent = Agent(
    name="Triage Agent",
    instructions=triage_instructions,
    model="gpt-4.1-2025-04-14", 
    handoffs=[booking_agent, billing_agent, maintenance_agent],
    input_guardrails=[support_input_guardrail],
)
# ----------------------------------------------------------------------------------------------------------------------------
# Paso 7: Definir la función principal para ejecutar el agente de triage (versión simplificada)
# ----------------------------------------------------------------------------------------------------------------------------
async def main():
    user_input = input("Bienvenido a Damian Resort Hotel: ")
    try:
        with trace("Damian Resort Hotel"):
            result = await Runner.run(triage_agent, user_input)
            print("Resultado final:", result.final_output)
    except InputGuardrailTripwireTriggered:
        print(
            "No puedo procesar tu solicitud. Por favor, reformula tu pregunta sobre reservas, "
            "facturación o mantenimiento del Damian Resort Hotel."
        )
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")


# ----------------------------------------------------------------------------------------------------------------------------
# Paso 8: Ejecutar el programa
# ----------------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    # Configuración específica para Windows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())